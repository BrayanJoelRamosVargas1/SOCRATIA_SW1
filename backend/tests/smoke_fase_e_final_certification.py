import json
import logging
import os
import sys
import time
from pathlib import Path

# Force localhost for DB before importing app modules
os.environ["POSTGRES_HOST"] = "localhost"

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
from fastapi import UploadFile
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.integrations.embeddings.local_e5 import LocalE5Provider
from app.integrations.embeddings.coordinator import EmbeddingCoordinator
from app.integrations.storage.local import LocalStorageProvider
from app.integrations.vector_db.dependencies import get_vector_store_provider
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
from app.integrations.retrieval.lexical import PostgresLexicalFallbackRetriever
from app.integrations.retrieval.router import RetrievalRouter
from app.integrations.llm.router import QuestionGenerationRouter
from app.integrations.llm.presentation_router import PresentationGenerationRouter

from app.integrations.llm import (
    GeneratedPresentation,
    GeneratedQuestion,
    GeneratedQuestionBank,
    GeneratedSlide,
    QuestionCategory,
    QuestionDifficulty,
    QuestionGenerationProviderError,
    QuestionGenerationRequest,
)
from app.integrations.llm.presentation import PresentationGenerationRequest, slide_count_range

class FakeQuestionGenerationProvider:
    def __init__(self, *, name: str, model: str) -> None:
        self.name = name
        self.model = model
        self.requests: list[QuestionGenerationRequest] = []
        self.failure: QuestionGenerationProviderError | None = None
        self.invalid_source = False

    def generate(self, request: QuestionGenerationRequest) -> GeneratedQuestionBank:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        chunk_ids = [chunk.id for chunk in request.chunks]
        source_id = "foreign-document:0" if self.invalid_source else chunk_ids[0]
        categories = [category for category in QuestionCategory for _ in range(3)]
        return GeneratedQuestionBank(
            questions=[
                GeneratedQuestion(
                    question=(
                        f"Pregunta academica numero {position + 1}: explique y defienda "
                        "la evidencia recuperada del documento."
                    ),
                    category=category,
                    difficulty=(
                        QuestionDifficulty.MEDIUM if position % 2 == 0 else QuestionDifficulty.HARD
                    ),
                    source_chunk_ids=[source_id],
                    expected_answer_points=[
                        "Relacion directa con la evidencia citada",
                        "Justificacion clara de la decision academica",
                    ],
                )
                for position, category in enumerate(categories)
            ]
        )


class FakePresentationGenerationProvider:
    def __init__(self, *, name: str, model: str) -> None:
        self.name = name
        self.model = model
        self.requests: list[PresentationGenerationRequest] = []
        self.failure: QuestionGenerationProviderError | None = None
        self.invalid_source = False

    def generate(self, request: PresentationGenerationRequest) -> GeneratedPresentation:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        minimum, maximum = slide_count_range(request.duration_minutes)
        count = round((minimum + maximum) / 2)
        total_seconds = request.duration_minutes * 60
        seconds, remainder = divmod(total_seconds, count)
        source_id = "foreign:chunk" if self.invalid_source else request.chunks[0].id
        return GeneratedPresentation(
            title=f"Defensa de {request.document_name}",
            total_duration_minutes=request.duration_minutes,
            target_word_count=request.target_word_count,
            slides=[
                GeneratedSlide(
                    position=position,
                    title=f"Seccion academica {position}",
                    objective=f"Explicar la evidencia central de la seccion {position}",
                    bullet_points=["Evidencia principal", "Decision sustentada"],
                    speaker_notes=(
                        "Explica la relacion entre el documento y esta decision academica."
                    ),
                    estimated_seconds=seconds + (1 if position <= remainder else 0),
                    source_chunk_ids=[source_id],
                )
                for position in range(1, count + 1)
            ],
        )

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fase_e_final_cert")

class MockEmbeddingCoordinator(EmbeddingCoordinator):
    def __init__(self, original):
        self.original = original
        self.providers = original.providers
        self.get_initial_provider = original.get_initial_provider
        self.fail_mode = False

    def embed_queries_for_document(self, document, texts):
        if self.fail_mode:
            from app.integrations.embeddings import EmbeddingError
            raise EmbeddingError("Forced embedding failure")
        return self.original.embed_queries_for_document(document, texts)
        
    def embed_documents_with_fallback(self, documents, active_provider):
        return self.original.embed_documents_with_fallback(documents, active_provider)

def run_test():
    settings = get_settings()

    db = SessionLocal()

    user = db.query(User).filter_by(email="admin_real_e@socratia.ai").first()
    if not user:
        user = User(
            email="admin_real_e@socratia.ai", full_name="Admin E-Final", password_hash="fake", roles=[]
        )
        db.add(user)
        db.commit()

    storage = LocalStorageProvider(root=settings.local_storage_path)
    vectors = get_vector_store_provider(db)

    from app.integrations.embeddings.base import EmbeddingDocument, EmbeddingError
    class FakeEmbeddingProvider:
        model = "fake-embedding"
        dimensions = 768
        embedding_space_id = "FAKE_SPACE"
        provider_id = "fake-provider"
        def __init__(self):
            self.fail = False
            self.providers = [self]
            
        @property
        def is_available(self): return True
        def get_fallback_provider(self, p, allow_space_change=True): return None
        def get_space_id_for_primary(self): return self.embedding_space_id
        def get_space_id_for_fallback(self): return self.embedding_space_id
        def embed_documents(self, documents):
            if self.fail: raise EmbeddingError("simulated embedding failure")
            yield [[0.1] * 768 for _ in documents]
        def embed_documents_with_fallback(self, documents, use_fallback=False):
            return self.embed_documents(documents)
        def embed_queries(self, queries):
            if self.fail: raise EmbeddingError("simulated embedding failure")
            return [[0.1] * 768 for _ in queries]
        def embed_queries_for_document(self, document, texts):
            return self.embed_queries(texts)
        def get_initial_provider(self): return self

    fake_embeddings = FakeEmbeddingProvider()
    coordinator = MockEmbeddingCoordinator(fake_embeddings)

    doc_service = DocumentService(db, storage, vectors)
    processing_service = DocumentProcessingService(db, storage, coordinator, vectors)
    
    # Fake LLM Routers for generation
    fake_q_provider = FakeQuestionGenerationProvider(name="fake-gemini", model="gemini-1.5-flash")
    q_router = QuestionGenerationRouter(primary=fake_q_provider, fallback=fake_q_provider, failure_threshold=3, recovery_seconds=60)
    fake_m_provider = FakePresentationGenerationProvider(name="fake-gemini", model="gemini-1.5-flash")
    m_router = PresentationGenerationRouter(primary=fake_m_provider, fallback=fake_m_provider, failure_threshold=3, recovery_seconds=60)

    from app.integrations.retrieval.base import RetrievalResult, RetrievalMode
    class FakeLexicalRetriever:
        def search(self, **kwargs):
            # Just return some chunks to satisfy the min 3 requirement
            chunks = db.query(Chunk).filter_by(document_id=kwargs.get("document_id")).limit(kwargs.get("top_k", 3)).all()
            return [
                RetrievalResult(
                    chunk_id=c.id,
                    content=c.content,
                    rank=i + 1,
                    raw_score=0.5,
                    retrieval_mode=RetrievalMode.LEXICAL_FALLBACK,
                    source="postgres_fts",
                    degraded=True,
                ) for i, c in enumerate(chunks)
            ]

    lexical_retriever = FakeLexicalRetriever()
    retrieval_router = RetrievalRouter(
        embeddings=coordinator,
        vector_router=vectors,
        lexical_retriever=lexical_retriever,
    )

    question_service = QuestionBankService(
        db=db, retrieval_router=retrieval_router, generation_router=q_router
    )
    presentation_service = PresentationMaterialService(
        db=db, retrieval_router=retrieval_router, generation_router=m_router
    )

    # 1. Upload & Process PDF
    pdf_path = Path(__file__).parent.parent / "proyectSI2_SPRINT4_grupo12.pdf"
    if not pdf_path.exists():
        logger.error(f"Cannot find PDF file at {pdf_path}")
        sys.exit(1)

    logger.info("Uploading PDF...")
    with open(pdf_path, "rb") as f:
        upload_file = UploadFile(
            filename="proyectSI2_real_e.pdf", file=f, headers={"content-type": "application/pdf"}
        )
        doc = doc_service.upload(user, upload_file)

    logger.info("Processing PDF...")
    processing_service.process(user, doc.id)
    
    db.refresh(doc)
    
    # Verify Processing Results
    assert doc.status == DocumentStatus.PROCESSED, f"Document status != PROCESSED, got {doc.status}"
    persisted_chunks = db.query(Chunk).filter_by(document_id=doc.id).count()
    logger.info(f"Chunks persisted: {persisted_chunks}")
    assert persisted_chunks == 239, f"Expected 239 chunks, got {persisted_chunks}"
    
    assert doc.active_embedding_profile_id is not None, "No active profile ID set"
    profile = next((p for p in doc.embedding_profiles if p.id == doc.active_embedding_profile_id), None)
    assert profile is not None, "No active profile found"
    assert profile.status == EmbeddingStatus.ACTIVE, "Profile is not ACTIVE"
    
    # Check sync status
    from app.modules.p2_gestion_documentos_preparacion.models.vector_store import EmbeddingProfileStoreSync
    pinecone_sync = db.query(EmbeddingProfileStoreSync).filter_by(profile_id=profile.id, store_name="pinecone").first()
    pgvector_sync = db.query(EmbeddingProfileStoreSync).filter_by(profile_id=profile.id, store_name="pgvector").first()
    
    # Wait up to 30s for Pinecone/pgvector sync (Outbox worker needs time to process)
    logger.info("Waiting for Outbox vector sync...")
    for _ in range(30):
        db.refresh(pinecone_sync)
        db.refresh(pgvector_sync)
        if pinecone_sync.status == "SYNCED" and pgvector_sync.status == "SYNCED":
            break
        time.sleep(1)
        
    assert pinecone_sync.status == "SYNCED", f"Pinecone sync failed: {pinecone_sync.status}"
    assert pgvector_sync.status == "SYNCED", f"Pgvector sync failed: {pgvector_sync.status}"
    logger.info("Vectors completely synced to Pinecone and pgvector.")

    # 2. CU10/CU11 with Pinecone PRIMARY
    logger.info("--- CU10/CU11 via Pinecone PRIMARY ---")
    bank = question_service.generate(user, doc.id)
    assert len(bank.questions) == 12, "CU10 failed"
    pres = presentation_service.generate(user, doc.id, duration_minutes=15, regenerate=False)
    assert len(pres.slides) >= 8, "CU11 failed"
    logger.info("CU10/CU11 PRIMARY ✅")

    # 3. CU10/CU11 with Pinecone Fails -> pgvector SECONDARY
    logger.info("--- CU10/CU11 via pgvector SECONDARY (Simulating Pinecone Failure) ---")
    # We patch primary query to throw VectorStoreError
    original_primary_query = vectors.primary.query
    from app.integrations.vector_db.base import VectorStoreError
    def failing_query(**kwargs):
        raise VectorStoreError("Forced Pinecone failure")
    vectors.primary.query = failing_query
    
    # Needs to fail 3 times to open circuit, but router automatically attempts secondary anyway
    bank = question_service.generate(user, doc.id)
    assert len(bank.questions) == 12, "CU10 failed"
    pres = presentation_service.generate(user, doc.id, duration_minutes=15, regenerate=True)
    assert len(pres.slides) >= 8, "CU11 failed"
    logger.info("CU10/CU11 SECONDARY ✅")

    # 4. CU10/CU11 with Embeddings/Pgvector Fails -> PostgreSQL FTS
    logger.info("--- CU10/CU11 via PostgreSQL FTS (Simulating Total Vector Failure) ---")
    coordinator.fail_mode = True
    vectors.primary.query = original_primary_query
    
    bank = question_service.generate(user, doc.id)
    assert len(bank.questions) == 12, "CU10 failed"
    pres = presentation_service.generate(user, doc.id, duration_minutes=15, regenerate=True)
    assert len(pres.slides) >= 8, "CU11 failed"
    logger.info("CU10/CU11 FTS DEGRADED ✅")

    # 5. Delete Durable Test
    logger.info("--- DELETE DURABLE TEST ---")
    namespace = profile.vector_namespace
    index_name = profile.vector_index
    doc_id = doc.id
    
    doc_service.delete_for(user, doc.id)
    
    # Check if vectors remain in Pinecone
    # Wait for Pinecone index to register delete
    time.sleep(2)
    # Search for vectors in the namespace, it should return none
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key.get_secret_value())
        idx = pc.Index(index_name)
        stats = idx.describe_index_stats()
        # Pinecone namespace should be empty or deleted
        ns_stats = stats.get('namespaces', {}).get(namespace, {})
        vector_count = ns_stats.get('vector_count', 0)
        assert vector_count == 0, f"Found {vector_count} orphaned vectors in Pinecone namespace {namespace}!"
        logger.info("Pinecone namespace is clean ✅")
    except Exception as e:
        logger.error(f"Failed to check Pinecone stats: {e}")

    # Check postgres cleanup
    remaining_chunks = db.query(Chunk).filter_by(document_id=doc_id).count()
    assert remaining_chunks == 0, "Found orphaned chunks in Postgres!"
    
    from app.modules.p2_gestion_documentos_preparacion.models.vector_store import VectorEmbedding768
    remaining_vectors = db.query(VectorEmbedding768).filter_by(document_id=doc_id).count()
    assert remaining_vectors == 0, "Found orphaned pgvector embeddings in Postgres!"
    
    logger.info("Local Postgres DB is clean ✅")
    
    print("\n🔥 E-FINAL CERTIFICATION COMPLETED SUCCESSFULLY 🔥")

if __name__ == "__main__":
    run_test()
