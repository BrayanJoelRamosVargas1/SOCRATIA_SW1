"""Run real CU11 primary and fallback smoke tests against the Docker stack."""

import json
import sys
import uuid

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.embeddings.dependencies import get_embedding_provider
from app.integrations.llm import LLMErrorKind, QuestionGenerationProviderError
from app.integrations.llm.dependencies import get_presentation_generation_router
from app.integrations.llm.presentation import (
    GeneratedPresentation,
    PresentationGenerationRequest,
)
from app.integrations.llm.presentation_router import PresentationGenerationRouter
from app.integrations.vector_db.dependencies import get_vector_store_provider
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.services.presentation_material_service import (
    PresentationMaterialService,
)
from scripts.smoke_cu10 import API_URL, build_document


class ForcedGeminiFailure:
    name = "gemini"
    model = "forced-smoke-failure"

    def generate(self, _: PresentationGenerationRequest) -> GeneratedPresentation:
        raise QuestionGenerationProviderError(
            "Forced primary failure for CU11 smoke",
            provider=self.name,
            kind=LLMErrorKind.TRANSIENT,
            detail="forced_smoke",
        )


def validate(material: dict[str, object], provider: str) -> None:
    slides = material.get("slides")
    if not isinstance(slides, list) or not 8 <= len(slides) <= 12:
        raise AssertionError("CU11 returned an invalid slide count")
    if material.get("provider_used") != provider:
        raise AssertionError(f"CU11 expected provider {provider}")
    total = 0
    for slide in slides:
        if not isinstance(slide, dict) or "source_chunk_ids" in slide:
            raise AssertionError("CU11 exposed an invalid public slide")
        total += int(slide["estimated_seconds"])
    if not 810 <= total <= 990:
        raise AssertionError("CU11 duration is outside tolerance")


def main() -> int:
    client = httpx.Client(base_url=API_URL, timeout=300)
    suffix = uuid.uuid4().hex[:12]
    response = client.post(
        "/auth/register",
        json={
            "email": f"cu11-smoke-{suffix}@example.com",
            "full_name": "CU11 Real Smoke",
            "password": f"Socratia presentation smoke {uuid.uuid4().hex}",
        },
    )
    response.raise_for_status()
    user_id = response.json()["user"]["id"]
    response = client.post(
        "/documents",
        files={
            "file": (
                "socratia-cu11-smoke.docx",
                build_document(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    response.raise_for_status()
    document_id = response.json()["id"]
    response = client.post(f"/documents/{document_id}/process")
    response.raise_for_status()
    chunk_count = response.json()["chunk_count"]
    response = client.post(
        f"/documents/{document_id}/presentation/generate",
        json={"duration_minutes": 15},
    )
    response.raise_for_status()
    primary = response.json()
    validate(primary, "gemini")

    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    configured = get_presentation_generation_router()
    router = PresentationGenerationRouter(
        primary=ForcedGeminiFailure(),
        fallback=configured.fallback,
        failure_threshold=1,
        recovery_seconds=60,
    )
    with Session(engine, expire_on_commit=False) as db:
        user = db.get(User, user_id)
        if user is None:
            raise AssertionError("Smoke user was not persisted")
        PresentationMaterialService(
            db=db,
            embeddings=get_embedding_provider(),
            vectors=get_vector_store_provider(),
            generation_router=router,
        ).generate(user, document_id, duration_minutes=15, regenerate=True)

    fallback = client.get(f"/documents/{document_id}/presentation")
    fallback.raise_for_status()
    material = fallback.json()
    validate(material, "groq")
    if material.get("fallback_used") is not True:
        raise AssertionError("CU11 fallback telemetry was not persisted")
    print(
        json.dumps(
            {
                "document_id": document_id,
                "chunk_count": chunk_count,
                "slide_count": len(material["slides"]),
                "duration_minutes": material["duration_minutes"],
                "primary_provider": primary["provider_used"],
                "fallback_provider": material["provider_used"],
                "fallback_used": material["fallback_used"],
                "status": material["status"],
            }
        )
    )
    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
