from app.core.database import SessionLocal
from app.integrations.embeddings.dependencies import get_embedding_provider
from app.integrations.llm.dependencies import (
    get_presentation_generation_router,
    get_question_generation_router,
)
from app.integrations.vector_db.base import (
    VectorSearchResult,
    VectorStoreError,
    VectorStoreProvider,
)
from app.integrations.vector_db.pgvector_provider import PgVectorStoreProvider
from app.integrations.vector_db.router import VectorStoreRouter
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.document import Document
from app.modules.p2_gestion_documentos_preparacion.models.vector_store import (
    EmbeddingProfileStoreSync,
)
from app.modules.p2_gestion_documentos_preparacion.services.presentation_material_service import (
    PresentationMaterialService,
)
from app.modules.p2_gestion_documentos_preparacion.services.question_bank_service import (
    QuestionBankService,
)


class FailingPineconeProvider(VectorStoreProvider):
    def upsert(self, **kwargs) -> None:
        raise NotImplementedError()

    def delete(self, **kwargs) -> None:
        raise NotImplementedError()

    def query(self, **kwargs) -> list[VectorSearchResult]:
        raise VectorStoreError("Forced Pinecone failure for E-4 testing")


def run_smoke_test():
    print("=== SMOKE TEST FASE E-4 (ACTUALIZADO CON CU10/CU11) ===")

    db = SessionLocal()

    try:
        # Encontramos un profile SYNCED en pgvector
        synced_profile = (
            db.query(EmbeddingProfileStoreSync)
            .filter_by(status="SYNCED", store_name="pgvector")
            .first()
        )
        if not synced_profile:
            print("No SYNCED profiles found in pgvector.")
            return

        profile_id = synced_profile.profile_id

        # Encontramos el Document asociado a este profile
        doc = db.query(Document).filter_by(embedding_profile_id=profile_id).first()
        if not doc:
            print(f"No Document found for profile {profile_id}")
            return

        document_id = doc.id
        user_id = doc.user_id
        user = db.get(User, user_id)

        print(f"Using Document: {document_id}, User: {user_id}, Profile: {profile_id}")

        primary = FailingPineconeProvider()
        secondary = PgVectorStoreProvider(db=db)

        router = VectorStoreRouter(
            primary=primary, secondary=secondary, db=db, circuit_breaker_timeout_sec=5
        )

        service_cu10 = QuestionBankService(
            db=db,
            embeddings=get_embedding_provider(),
            vectors=router,
            generation_router=get_question_generation_router(),
        )

        service_cu11 = PresentationMaterialService(
            db=db,
            embeddings=get_embedding_provider(),
            vectors=router,
            generation_router=get_presentation_generation_router(),
        )

        print("\n--- TEST 1: Fallback a pgvector SYNCED ---")
        try:
            print("Ejecutando CU10 Pinecone->pgvector...")
            bank = service_cu10.generate(user, document_id)
            if len(bank.questions) == 12:
                print("✅ CU10 Pinecone->pgvector COMPLETADO (12 preguntas generadas)")
            else:
                print(f"❌ CU10 Falló: {len(bank.questions)} preguntas.")

            print("Ejecutando CU11 Pinecone->pgvector...")
            # Cleanup previous presentation if exists to force generation
            from app.modules.p2_gestion_documentos_preparacion.models.presentation_material import (
                PresentationMaterial,
            )

            db.query(PresentationMaterial).filter_by(document_id=document_id).delete()
            db.commit()

            presentation = service_cu11.generate(
                user, document_id, duration_minutes=15, regenerate=True
            )
            if 8 <= len(presentation.slides) <= 12:
                print(f"✅ CU11 Pinecone->pgvector COMPLETADO ({len(presentation.slides)} slides)")
            else:
                print(f"❌ CU11 Falló: {len(presentation.slides)} slides.")

        except Exception as e:
            print(f"❌ TEST 1 Falló con excepción: {e}")
            import traceback

            traceback.print_exc()

        print("\n--- TEST 2: Fallback a pgvector PENDING ---")
        synced_profile.status = "PENDING"
        db.commit()

        try:
            print("Ejecutando CU10 Pinecone->pgvector (PENDING)...")
            service_cu10.generate(user, document_id)
            print(
                "❌ TEST 2 Falló: CU10 generó preguntas cuando debió fallar por pgvector PENDING."
            )
        except Exception as e:
            if "not completely SYNCED" in str(e) or "VectorStoreError" in str(type(e).__name__):
                print(f"✅ pgvector PENDING -> rechazado correctamente. Error capturado: {e}")
            else:
                print(f"❓ TEST 2: Falla capturada pero error inesperado: {e}")

        # Restore status
        synced_profile.status = "SYNCED"
        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    run_smoke_test()
