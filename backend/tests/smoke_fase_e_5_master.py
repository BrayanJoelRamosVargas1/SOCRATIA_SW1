from app.core.database import SessionLocal
from app.integrations.embeddings import EmbeddingCoordinator, EmbeddingError
from app.integrations.llm.dependencies import (
    get_presentation_generation_router,
    get_question_generation_router,
)
from app.integrations.retrieval.lexical import PostgresLexicalFallbackRetriever
from app.integrations.retrieval.router import RetrievalRouter
from app.integrations.vector_db.base import (
    VectorSearchResult,
    VectorStoreError,
    VectorStoreProvider,
)
from app.integrations.vector_db.router import VectorStoreRouter
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.document import (
    Document,
    DocumentChunk,
    DocumentStatus,
)
from app.modules.p2_gestion_documentos_preparacion.models.vector_store import (
    EmbeddingProfileStoreSync,
)
from app.modules.p2_gestion_documentos_preparacion.services.presentation_material_service import (
    PresentationMaterialService,
)
from app.modules.p2_gestion_documentos_preparacion.services.question_bank_service import (
    QuestionBankService,
)


class FailingEmbeddingCoordinator(EmbeddingCoordinator):
    def __init__(self):
        # We don't initialize the real providers, just mock failure
        pass

    def embed_queries_for_document(self, document, texts: list[str]) -> list[list[float]]:
        # Simulate all providers failing (Gemini, Cohere, HF E5, Local E5)
        raise EmbeddingError("All embedding providers (Gemini, Cohere, HF E5, Local E5) failed!")


class FailingVectorStoreProvider(VectorStoreProvider):
    def __init__(self, name: str):
        self.name = name

    @property
    def provider_name(self) -> str:
        return self.name

    def upsert(self, **kwargs) -> None:
        raise NotImplementedError()

    def delete(self, **kwargs) -> None:
        raise NotImplementedError()

    def query(self, **kwargs) -> list[VectorSearchResult]:
        raise VectorStoreError(f"Forced {self.name} failure for E-5 testing")


def run_smoke_test():
    print("=== SMOKE TEST FASE E-5 (GRACEFUL DEGRADATION MAESTRO) ===")
    print("Simulando fallo catastrófico:")
    print("Gemini Embeddings ❌")
    print("Cohere Embed      ❌")
    print("HF E5 Remote      ❌")
    print("Local E5          ❌")
    print("Pinecone          ❌")
    print("pgvector          ❌")
    print("PostgreSQL FTS    ✅")

    db = SessionLocal()

    try:
        # 1. Encontramos un profile SYNCED
        synced_profile = db.query(EmbeddingProfileStoreSync).filter_by(status="SYNCED").first()
        if not synced_profile:
            print("No SYNCED profiles found. Por favor, asegúrese de que existan perfiles.")
            return

        profile_id = synced_profile.profile_id

        # 2. Encontramos el Document asociado a este profile
        doc = db.query(Document).filter_by(active_embedding_profile_id=profile_id).first()
        if not doc:
            print(f"No Document found for profile {profile_id}")
            return

        document_id = doc.id
        user_id = doc.user_id
        user = db.get(User, user_id)

        print(f"\nUsando Document: {document_id}, User: {user_id}, Profile: {profile_id}")

        # 3. Setup de las dependencias "Rotas"
        primary_vector = FailingVectorStoreProvider("pinecone")
        secondary_vector = FailingVectorStoreProvider("pgvector")

        vector_router = VectorStoreRouter(
            primary=primary_vector, secondary=secondary_vector, db=db, circuit_breaker_timeout_sec=5
        )

        failing_embeddings = FailingEmbeddingCoordinator()

        # 4. Setup del Retriever FTS "Sano" y el Router de Recuperación
        lexical_retriever = PostgresLexicalFallbackRetriever(db)

        retrieval_router = RetrievalRouter(
            embeddings=failing_embeddings,
            vector_router=vector_router,
            lexical_retriever=lexical_retriever,
        )

        from app.integrations.llm.router import QuestionGenerationRouter
        from app.integrations.llm.presentation_router import PresentationGenerationRouter
        from tests.conftest import FakeQuestionGenerationProvider, FakePresentationGenerationProvider

        fake_q_provider = FakeQuestionGenerationProvider(name="fake-gemini", model="gemini-1.5-flash")
        q_router = QuestionGenerationRouter(primary=fake_q_provider, fallback=fake_q_provider, failure_threshold=3, recovery_seconds=60)

        fake_m_provider = FakePresentationGenerationProvider(name="fake-gemini", model="gemini-1.5-flash")
        m_router = PresentationGenerationRouter(primary=fake_m_provider, fallback=fake_m_provider, failure_threshold=3, recovery_seconds=60)

        # 5. Inyectamos las dependencias en los servicios
        service_cu10 = QuestionBankService(
            db=db,
            retrieval_router=retrieval_router,
            generation_router=q_router,
        )

        service_cu11 = PresentationMaterialService(
            db=db,
            retrieval_router=retrieval_router,
            generation_router=m_router,
        )

        # 6. Test FTS Native (Verify exact match)
        print("\n--- TEST FTS Nativo ---")
        from app.modules.p2_gestion_documentos_preparacion.models.document import EmbeddingProfile
        profile = db.get(EmbeddingProfile, profile_id)
        chunk_set_id = profile.chunk_set_id

        dummy_chunk_existing = db.query(DocumentChunk).filter_by(
            chunk_set_id=chunk_set_id, chunk_index=9999
        ).first()
        if dummy_chunk_existing:
            db.delete(dummy_chunk_existing)
            db.commit()

        dummy_chunk = DocumentChunk(
            document_id=document_id,
            chunk_set_id=chunk_set_id,
            content="Este texto detalla la arquitectura monolítica modular para pruebas FTS. Garantiza resiliencia.",
            chunk_index=9999,
            start_char=0,
            end_char=100
        )
        db.add(dummy_chunk)
        db.commit()
        db.refresh(dummy_chunk)

        print("Insertado chunk dummy con 'arquitectura monolítica modular'.")

        fts_query = "arquitectura monolítica modular"
        results = lexical_retriever.search(
            document_id=document_id,
            user_id=user_id,
            chunk_set_id=chunk_set_id,
            query_text=fts_query,
            top_k=3,
        )
        found_dummy = False
        for res in results:
            if res.chunk_id == dummy_chunk.id:
                found_dummy = True
                print(
                    f"✅ FTS encontró exitosamente el chunk dummy. Score: {res.raw_score}, Rank: {res.rank}"
                )
                break

        if not found_dummy:
            print("❌ FTS falló en encontrar el chunk dummy.")

        print("\n--- TEST CU10: Generación de Preguntas via FTS ---")
        try:
            bank = service_cu10.generate(user, document_id)
            if len(bank.questions) == 12:
                print("✅ CU10 100% PostgreSQL FTS COMPLETADO (12 preguntas generadas)")
            else:
                print(f"❌ CU10 Falló: {len(bank.questions)} preguntas.")

            db.refresh(doc)
            if doc.status == DocumentStatus.PROCESSED:
                print("✅ Document status sigue siendo PROCESSED (no se modificó erróneamente).")
            else:
                print(f"❌ Document status modificado erróneamente a: {doc.status}")
        except Exception as e:
            print(f"❌ TEST CU10 Falló con excepción: {e}")
            import traceback

            traceback.print_exc()

        print("\n--- TEST CU11: Generación de Material de Presentación via FTS ---")
        try:
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
                print(f"✅ CU11 100% PostgreSQL FTS COMPLETADO ({len(presentation.slides)} slides)")
            else:
                print(f"❌ CU11 Falló: {len(presentation.slides)} slides.")
        except Exception as e:
            print(f"❌ TEST CU11 Falló con excepción: {e}")
            import traceback

            traceback.print_exc()

        print("\n🔥 Test Maestro Finalizado 🔥")

    finally:
        db.close()


if __name__ == "__main__":
    run_smoke_test()
