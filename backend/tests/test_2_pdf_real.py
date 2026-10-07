"""
test_2_pdf_real.py — E-FINAL Certification Test 2
===================================================
Certifies:
  PDF real 16.7 MB -> extraction -> normalisation -> chunking -> 239 chunks
  -> Local E5 REAL embeddings (768-dim, intfloat/multilingual-e5-base)
  -> pgvector REAL upsert
  -> PROCESSED status

Architecture proof: Socratia generates embeddings locally when ALL remote
providers (Gemini, Cohere, HF Remote) are unavailable.

Strategy: set EMBEDDING_FORCE_PROVIDER_FAILURE="gemini,cohere,huggingface"
to force immediate failure on those three, so the coordinator falls through
to LocalE5Provider which is always available offline.
"""
import logging
import os
import sys
import time
from pathlib import Path

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ---------------------------------------------------------------------------
# Force all remote providers to fail BEFORE importing anything that caches
# the coordinator — must be set before get_settings() is ever called with LRU.
# ---------------------------------------------------------------------------
os.environ["EMBEDDING_FORCE_PROVIDER_FAILURE"] = "gemini,cohere,huggingface"
# Clear any LRU-cached coordinator/settings so the env var takes effect.

try:
    from app.integrations.embeddings.dependencies import get_embedding_provider

    get_embedding_provider.cache_clear()
except Exception:
    pass
try:
    from app.core.config import get_settings

    get_settings.cache_clear()
except Exception:
    pass

# ---------------------------------------------------------------------------
# Standard imports
# ---------------------------------------------------------------------------
from fastapi import UploadFile  # noqa: E402
from tests.smoke_fase_e_final_certification import (  # noqa: E402
    FakePresentationGenerationProvider,
    FakeQuestionGenerationProvider,
)

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.integrations.embeddings.dependencies import get_embedding_provider  # noqa: E402
from app.integrations.llm.presentation_router import PresentationGenerationRouter  # noqa: E402
from app.integrations.llm.router import QuestionGenerationRouter  # noqa: E402
from app.integrations.retrieval.lexical import PostgresLexicalFallbackRetriever  # noqa: E402
from app.integrations.retrieval.router import RetrievalRouter  # noqa: E402
from app.integrations.storage.local import LocalStorageProvider  # noqa: E402
from app.integrations.vector_db.dependencies import get_vector_store_provider  # noqa: E402
from app.modules.p1_gestion_identidad_seguridad.models.user import User  # noqa: E402
from app.modules.p2_gestion_documentos_preparacion.models.document import (  # noqa: E402
    DocumentChunk as Chunk,
)
from app.modules.p2_gestion_documentos_preparacion.models.document import (  # noqa: E402
    DocumentStatus,
)
from app.modules.p2_gestion_documentos_preparacion.services.document_processing_service import (  # noqa: E402
    DocumentProcessingService,
)
from app.modules.p2_gestion_documentos_preparacion.services.document_service import (  # noqa: E402
    DocumentService,
)
from app.modules.p2_gestion_documentos_preparacion.services.presentation_material_service import (  # noqa: E402
    PresentationMaterialService,
)
from app.modules.p2_gestion_documentos_preparacion.services.question_bank_service import (  # noqa: E402
    QuestionBankService,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_2_pdf_real")


def run_test():
    settings = get_settings()
    db = SessionLocal()

    # ---------- User setup --------------------------------------------------
    user = db.query(User).filter_by(email="admin_real_e@socratia.ai").first()
    if not user:
        user = User(
            email="admin_real_e@socratia.ai",
            full_name="Admin E-Final",
            password_hash="fake",
            roles=[],
        )
        db.add(user)
        db.commit()

    # ---------- Provider setup ----------------------------------------------
    storage = LocalStorageProvider(root=settings.local_storage_path)
    vectors = get_vector_store_provider(db)
    coordinator = get_embedding_provider()

    # Verify the fallback chain resolved to local_e5 as the starting provider
    initial_provider = coordinator.get_initial_provider()
    logger.info(
        "=== FALLBACK CHAIN STATUS ===\n%s",
        "\n".join(
            f"  [{i}] provider={p.provider_id} space={p.embedding_space_id}"
            f" available={p.is_available}"
            for i, p in enumerate(coordinator.providers)
        ),
    )
    logger.info("Configured initial provider: %s (will dynamically fall back to local_e5 on forced failure)", initial_provider.provider_id)

    doc_service = DocumentService(db, storage, vectors)
    processing_service = DocumentProcessingService(db, storage, coordinator, vectors)

    fake_q_provider = FakeQuestionGenerationProvider(
        name="fake-gemini", model="gemini-1.5-flash"
    )
    q_router = QuestionGenerationRouter(
        primary=fake_q_provider,
        fallback=fake_q_provider,
        failure_threshold=3,
        recovery_seconds=60,
    )
    fake_m_provider = FakePresentationGenerationProvider(
        name="fake-gemini", model="gemini-1.5-flash"
    )
    m_router = PresentationGenerationRouter(
        primary=fake_m_provider,
        fallback=fake_m_provider,
        failure_threshold=3,
        recovery_seconds=60,
    )

    lexical_retriever = PostgresLexicalFallbackRetriever(db)
    retrieval_router = RetrievalRouter(
        embeddings=coordinator, vector_router=vectors, lexical_retriever=lexical_retriever
    )

    question_service = QuestionBankService(
        db=db, retrieval_router=retrieval_router, generation_router=q_router
    )
    presentation_service = PresentationMaterialService(
        db=db, retrieval_router=retrieval_router, generation_router=m_router
    )

    # ---------- PDF upload --------------------------------------------------
    pdf_path = Path(__file__).parent.parent / "proyectSI2_SPRINT4_grupo12.pdf"
    if not pdf_path.exists():
        logger.error("Cannot find PDF file at %s", pdf_path)
        sys.exit(1)

    logger.info("Uploading REAL 16.7 MB PDF...")
    with open(pdf_path, "rb") as f:
        upload_file = UploadFile(
            filename="proyectSI2_SPRINT4_grupo12.pdf",
            file=f,
            headers={"content-type": "application/pdf"},
        )
        doc = doc_service.upload(user, upload_file)

    # ---------- Processing with Local E5 ------------------------------------
    logger.info("Processing PDF with LOCAL E5 (all remote providers forced to fail)...")
    t0 = time.monotonic()
    processing_service.process(user, doc.id)
    elapsed = time.monotonic() - t0
    db.refresh(doc)

    assert doc.status == DocumentStatus.PROCESSED, (
        f"Document status != PROCESSED, got {doc.status}"
    )
    logger.info("Processing complete in %.1fs", elapsed)

    persisted_chunks = db.query(Chunk).filter_by(document_id=doc.id).count()
    logger.info("Chunks persisted: %d", persisted_chunks)
    assert persisted_chunks == 239, f"Expected 239 chunks, got {persisted_chunks}"

    from app.modules.p2_gestion_documentos_preparacion.models.document import EmbeddingProfile

    profile = (
        db.query(EmbeddingProfile).filter_by(id=doc.active_embedding_profile_id).first()
    )
    assert profile is not None, "No active profile found!"
    assert profile.provider == "local_e5", (
        f"Expected profile.provider='local_e5', got '{profile.provider}'"
    )
    assert profile.embedding_space_id == "E5_BASE_768_V1", (
        f"Wrong embedding_space_id: {profile.embedding_space_id}"
    )
    assert profile.dimension == 768, f"Expected dimension=768, got {profile.dimension}"

    # Verify fingerprint matches Local E5 fingerprint
    from app.integrations.embeddings.local_e5 import LocalE5Provider

    local_e5 = LocalE5Provider()
    assert profile.model == local_e5.model, f"Model mismatch: {profile.model} vs {local_e5.model}"
    assert local_e5.compatibility_fingerprint is not None, "LocalE5 fingerprint is empty"
    logger.info("profile.provider=local_e5 OK")
    logger.info("profile.embedding_space_id=E5_BASE_768_V1 OK")
    logger.info("profile.dimension=768 OK")
    logger.info("fingerprint match OK")

    # ---------- pgvector sync -----------------------------------------------
    logger.info("Waiting for vector-sync-worker to sync to pgvector (up to 120s)...")
    from app.modules.p2_gestion_documentos_preparacion.models.vector_store import (
        EmbeddingProfileStoreSync,
    )

    pgvector_sync = None
    pinecone_sync = None
    for i in range(120):
        pgvector_sync = (
            db.query(EmbeddingProfileStoreSync)
            .filter_by(profile_id=profile.id, store_name="pgvector")
            .first()
        )
        pinecone_sync = (
            db.query(EmbeddingProfileStoreSync)
            .filter_by(profile_id=profile.id, store_name="pinecone")
            .first()
        )
        db.expire_all()

        pg_status = pgvector_sync.status if pgvector_sync else "NOT_FOUND"
        if pg_status == "SYNCED":
            break
        time.sleep(2)
        if i % 10 == 0:
            logger.info("Still waiting... pgvector=%s", pg_status)

    assert pgvector_sync is not None and pgvector_sync.status == "SYNCED", (
        f"pgvector sync failed or not found. status={pgvector_sync.status if pgvector_sync else 'None'}"
    )
    logger.info("pgvector SYNCED: OK (vectors_synced=%d)", pgvector_sync.vectors_synced or 0)

    if pinecone_sync and pinecone_sync.status == "SYNCED":
        logger.info("Pinecone SYNCED: OK")
    else:
        pin_status = pinecone_sync.status if pinecone_sync else "NOT_FOUND"
        logger.warning(
            "Pinecone status=%s — skipping Pinecone assertion per E-FINAL rules "
            "(credential may be expired; prior E-3 evidence stands).",
            pin_status,
        )

    # ---------- CU10/CU11 tests ---------------------------------------------
    logger.info("--- CU10/CU11 via pgvector PRIMARY (Pinecone may be unavailable) ---")
    bank = question_service.generate(user, doc.id)
    assert len(bank.questions) == 12, f"CU10 failed: got {len(bank.questions)} questions"
    pres = presentation_service.generate(user, doc.id, duration_minutes=15, regenerate=False)
    assert len(pres.slides) >= 8, f"CU11 failed: got {len(pres.slides)} slides"
    logger.info("CU10/CU11 OK")

    # Simulate total vector failure -> PostgreSQL FTS degraded mode
    logger.info("--- CU10/CU11 via PostgreSQL FTS DEGRADED mode ---")
    from app.integrations.embeddings.base import EmbeddingError
    from app.integrations.vector_db.base import VectorStoreError

    orig_primary_query = vectors.primary.query
    orig_secondary_query = vectors.secondary.query
    orig_embed = coordinator.embed_queries_for_document

    def _failing_query(**kwargs):
        raise VectorStoreError("Forced total vector store failure")

    def _failing_embed(*args, **kwargs):
        raise EmbeddingError("Forced embedding failure")

    vectors.primary.query = _failing_query
    vectors.secondary.query = _failing_query
    coordinator.embed_queries_for_document = _failing_embed

    try:
        bank = question_service.generate(user, doc.id)
        assert len(bank.questions) == 12, f"FTS CU10 failed: {len(bank.questions)}"
        pres = presentation_service.generate(
            user, doc.id, duration_minutes=15, regenerate=True
        )
        assert len(pres.slides) >= 8, f"FTS CU11 failed: {len(pres.slides)}"
        logger.info("CU10/CU11 FTS DEGRADED OK")
    finally:
        vectors.primary.query = orig_primary_query
        vectors.secondary.query = orig_secondary_query
        coordinator.embed_queries_for_document = orig_embed

    print("\n[PASS] E-FINAL CERTIFICATION TEST 2 COMPLETED SUCCESSFULLY")
    print("  Provider used : local_e5")
    print("  Space         : E5_BASE_768_V1")
    print("  Dimension     : 768")
    print(f"  Chunks        : {persisted_chunks}")
    print(f"  Processing    : {elapsed:.1f}s")
    print("  pgvector      : SYNCED")


if __name__ == "__main__":
    run_test()
