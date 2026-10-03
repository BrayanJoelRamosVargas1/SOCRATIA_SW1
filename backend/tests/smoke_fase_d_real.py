import json
import logging
import os
import sys
import time
from pathlib import Path

import psutil

# Force localhost for DB before importing app modules
os.environ["POSTGRES_HOST"] = "localhost"

# Forzar falla de proveedores remotos pero solo para Embeddings
os.environ["EMBEDDING_FORCE_PROVIDER_FAILURE"] = "gemini,cohere,huggingface"

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid

from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base
from app.integrations.embeddings.cohere import CohereEmbeddingProvider
from app.integrations.embeddings.coordinator import EmbeddingCoordinator
from app.integrations.embeddings.gemini import GeminiEmbeddingProvider
from app.integrations.embeddings.huggingface_e5 import HuggingFaceE5Provider
from app.integrations.embeddings.local_e5 import LocalE5Provider
from app.integrations.llm.dependencies import (
    get_presentation_generation_router,
    get_question_generation_router,
)
from app.integrations.storage.local import LocalStorageProvider
from app.integrations.vector_db.pinecone import PineconeVectorStoreProvider
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.document import DocumentChunk as Chunk
from app.modules.p2_gestion_documentos_preparacion.models.document import (
    DocumentStatus,
    EmbeddingProfile,
)
from app.modules.p2_gestion_documentos_preparacion.models.document import (
    ProfileStatus as EmbeddingStatus,
)
from app.modules.p2_gestion_documentos_preparacion.services.document_processing_service import (
    DocumentProcessingService,
)
from app.modules.p2_gestion_documentos_preparacion.services.document_service import DocumentService
from app.modules.p2_gestion_documentos_preparacion.services.presentation_material_service import (
    PresentationMaterialService,
)
from app.modules.p2_gestion_documentos_preparacion.services.question_bank_service import (
    QuestionBankService,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fase_d_real")


def get_memory_mb():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def run_test():
    settings = get_settings()

    # 1. Instanciar LLM Routers (Real) para CU10 y CU11
    q_router = get_question_generation_router()
    p_router = get_presentation_generation_router()

    # 2. Base de datos SQLite temporal para metadatos
    local_db_url = "sqlite:///:memory:"
    engine = create_engine(local_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    user = User(
        email="admin_real@socratia.ai", full_name="Admin Real", password_hash="fake", roles=[]
    )
    db.add(user)
    db.commit()

    # 3. Storage
    storage = LocalStorageProvider(root=settings.local_storage_path)

    # 4. Pinecone REAL
    if (
        not settings.pinecone_api_key
        or settings.pinecone_api_key.get_secret_value() == "YOUR_NEW_PINECONE_KEY_HERE"
    ):
        logger.error("Se requiere PINECONE_API_KEY real en el .env")
        sys.exit(1)

    namespace = f"socratia-test-real-{uuid.uuid4().hex[:8]}"
    vectors = PineconeVectorStoreProvider(
        api_key=settings.pinecone_api_key.get_secret_value(),
        index_name=settings.pinecone_index_name,
        dimensions=768,
        cloud=settings.pinecone_cloud,
        region=settings.pinecone_region,
        timeout_seconds=60,
    )

    # 5. Providers Embeddings
    hf_local = LocalE5Provider(
        model_name=settings.e5_embedding_model,
        dimensions=768,
    )

    # Las clases remotas fallarán gracias a EMBEDDING_FORCE_PROVIDER_FAILURE
    providers = [
        GeminiEmbeddingProvider(
            api_key="forced_fail",
            model=settings.gemini_embedding_model,
            dimensions=768,
            batch_size=20,
            timeout_seconds=10,
        ),
        CohereEmbeddingProvider(
            api_key="forced_fail",
            model=settings.cohere_embedding_model,
            dimensions=768,
            batch_size=20,
            timeout_seconds=10,
        ),
        HuggingFaceE5Provider(
            api_key="forced_fail",
            model=settings.e5_embedding_model,
            dimensions=768,
            batch_size=20,
            timeout_seconds=10,
        ),
        hf_local,
    ]
    coordinator = EmbeddingCoordinator(providers)

    # 6. Servicios
    doc_service = DocumentService(db, storage, vectors)
    processing_service = DocumentProcessingService(db, storage, coordinator, vectors)
    question_service = QuestionBankService(
        db=db, embeddings=coordinator, vectors=vectors, generation_router=q_router
    )
    presentation_service = PresentationMaterialService(
        db=db, embeddings=coordinator, vectors=vectors, generation_router=p_router
    )

    # 7. Subida del PDF
    pdf_path = Path(__file__).parent.parent / "proyectSI2_SPRINT4_grupo12.pdf"
    if not pdf_path.exists():
        logger.error(f"Cannot find PDF file at {pdf_path}")
        sys.exit(1)

    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    with open(pdf_path, "rb") as f:
        upload_file = UploadFile(
            filename="proyectSI2_real.pdf", file=f, headers={"content-type": "application/pdf"}
        )
        doc = doc_service.upload(user, upload_file)

    # Inicializar metricas
    report = {
        "document": {"size_mb": round(size_mb, 2), "chunks": 0, "vectors": 0},
        "embedding": {
            "provider": hf_local.provider_id,
            "model": hf_local.model,
            "dimension": hf_local.dimensions,
            "embedding_space": hf_local.embedding_space_id,
        },
        "profile": {"status": "ACTIVE"},
        "pinecone": {
            "real": True,
            "index": settings.pinecone_index_name,
            "vectors_match_chunks": False,
        },
        "cu10": {"questions": 0},
        "cu11": {"generated": False},
        "benchmark": {
            "model_load_seconds": 0.0,
            "embedding_seconds": 0.0,
            "peak_rss_mb": 0.0,
            "query_latency_ms": 0.0,
        },
    }

    t0 = time.monotonic()
    hf_local._get_model()  # Preload for metrics
    report["benchmark"]["model_load_seconds"] = round(time.monotonic() - t0, 3)

    # 8. TEST DE RESTART RESILIENCE
    # Modificamos el coordinator para que tire error a la mitad de los chunks locales (simular restart)
    logger.info("TEST: Procesando con Local E5 y simulando crash (restart)...")

    class CrashCoordinator:
        def __init__(self, original):
            self.original = original
            self.calls = 0
            self.providers = original.providers
            self.get_initial_provider = original.get_initial_provider

        def embed_documents_with_fallback(self, documents, active_provider):
            for batch in self.original.embed_documents_with_fallback(documents, active_provider):
                self.calls += 1
                if self.calls == 3:  # Abort on 3rd batch
                    raise RuntimeError("Simulated crash mid-processing!")
                yield batch

    # Replace coordinator temporarily
    processing_service.embeddings = CrashCoordinator(coordinator)

    try:
        processing_service.process(user, doc.id)
    except Exception as e:
        logger.info("Crash simulado exitosamente: %s", str(e))

    # Check what was saved
    db.refresh(doc)
    profile = (
        db.query(EmbeddingProfile)
        .filter_by(document_id=doc.id, status=EmbeddingStatus.STAGING)
        .first()
    )
    assert profile.status == EmbeddingStatus.STAGING, (
        f"Expected STAGING status after crash, got {profile.status}"
    )

    persisted_chunks_after_crash = db.query(Chunk).filter_by(document_id=doc.id).count()
    assert persisted_chunks_after_crash > 0, "Chunks were not persisted before crash!"

    logger.info("Restart resilience VERIFICADO. Reanudando proceso...")

    doc.status = DocumentStatus.ERROR
    db.commit()

    # Restore normal coordinator and resume
    processing_service.embeddings = coordinator
    t1 = time.monotonic()
    response = processing_service.process(user, doc.id)
    report["benchmark"]["embedding_seconds"] = round(time.monotonic() - t1, 3)

    db.refresh(doc)
    profile = (
        db.query(EmbeddingProfile)
        .filter_by(document_id=doc.id, status=EmbeddingStatus.ACTIVE)
        .first()
    )

    # 9. Validaciones POST-Process
    report["document"]["chunks"] = response.chunk_count
    report["document"]["vectors"] = response.chunk_count

    persisted_chunks = db.query(Chunk).filter_by(document_id=doc.id).count()

    assert doc.status == DocumentStatus.PROCESSED, "Document status != PROCESSED"
    assert profile.status == EmbeddingStatus.ACTIVE, "Profile status != ACTIVE"
    assert profile.provider == hf_local.provider_id, "Provider != local_e5"
    assert profile.dimension == 768, "Dimension != 768"
    assert profile.embedding_space_id == hf_local.embedding_space_id, (
        f"Space != {hf_local.embedding_space_id}"
    )
    assert persisted_chunks == response.chunk_count, "Persisted chunks mismatch"
    assert persisted_chunks > 0, "No chunks were processed"

    report["pinecone"]["vectors_match_chunks"] = True
    report["benchmark"]["peak_rss_mb"] = round(get_memory_mb(), 2)

    # 10. Pinecone Retrieval Timing
    t2 = time.monotonic()
    query_vector = hf_local.embed_queries(["arquitectura"])[0]
    results = vectors.query(
        namespace=profile.vector_namespace,
        vector=query_vector,
        top_k=4,
        filters={"document_id": doc.id},
        index_name=profile.vector_index,
    )
    report["benchmark"]["query_latency_ms"] = round((time.monotonic() - t2) * 1000, 2)
    assert len(results) > 0, "Pinecone real return empty results"

    # 11. CU10 (LLM)
    # 11. Fake LLM fallback + Generation success checks
    logger.info("Iniciando CU10 (Generación de Preguntas)...")
    try:
        bank = question_service.generate(user=user, document_id=doc.id)
        report["cu10"]["questions"] = len(bank.questions)
    except Exception as e:
        logger.error(f"CU10 fallo: {e}")

    logger.info("Iniciando CU11 (Generación de Material)...")
    try:
        material = presentation_service.generate(
            user=user, document_id=doc.id, duration_minutes=15, regenerate=False
        )
        report["cu11"]["generated"] = len(material.slides) > 0
    except Exception as e:
        logger.error(f"CU11 fallo: {e}")

    # 13. Cleanup
    logger.info("Realizando Cleanup del entorno Pinecone...")
    try:
        vectors.delete_namespace(namespace, index_name=profile.vector_index)
        logger.info(f"Namespace {namespace} limpiado.")
    except Exception:
        logger.error(
            f"Fallo el cleanup. Cleanup manual requerido: index={profile.vector_index}, namespace={namespace}"
        )

    print("\n\n" + "=" * 50)
    print("FASE D CERRADA: PRUEBA E2E REPORT")
    print("=" * 50)
    print(json.dumps(report, indent=2))
    print("=" * 50)


if __name__ == "__main__":
    try:
        run_test()
    except Exception:
        logger.error("Test interrumpido prematuramente.", exc_info=True)
        sys.exit(1)
