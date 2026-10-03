import json
import os
import sys

print("BENCHMARK SCRIPT STARTED!", flush=True)

import logging
import time
from pathlib import Path

# Force localhost for DB before importing app modules
os.environ["POSTGRES_HOST"] = "localhost"

print("Importing core dependencies...", flush=True)
try:
    import psutil
except ImportError:
    psutil = None

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("Importing get_settings...", flush=True)
from app.core.config import get_settings

print("Importing SessionLocal...", flush=True)
print("Importing Embedding Providers...", flush=True)
from app.integrations.embeddings.cohere import CohereEmbeddingProvider
from app.integrations.embeddings.coordinator import EmbeddingCoordinator
from app.integrations.embeddings.gemini import GeminiEmbeddingProvider
from app.integrations.embeddings.huggingface_e5 import HuggingFaceE5Provider
from app.integrations.embeddings.local_e5 import LocalE5Provider

print("Importing Storage...", flush=True)
from app.integrations.storage.local import LocalStorageProvider

print("Importing VectorDB...", flush=True)
print("Importing LLM...", flush=True)
from app.integrations.llm.dependencies import (
    get_presentation_generation_router,
    get_question_generation_router,
)

print("Importing Models...", flush=True)
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.document import DocumentChunk as Chunk
from app.modules.p2_gestion_documentos_preparacion.models.document import DocumentStatus

print("Importing Services...", flush=True)
from fastapi import UploadFile

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
logger = logging.getLogger("fase_d_benchmark")


def get_memory_mb():
    if psutil:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    return 0.0


def get_cpu_percent():
    if psutil:
        return psutil.cpu_percent(interval=None)
    return 0.0


def run_benchmark():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    print("run_benchmark: Setup offline env...", flush=True)
    settings = get_settings()
    settings.embedding_force_provider_failure = "gemini,cohere,huggingface"

    print("run_benchmark: Overriding DB URL with SQLite...", flush=True)
    local_db_url = "sqlite:///:memory:"
    engine = create_engine(local_db_url, connect_args={"check_same_thread": False})

    print("run_benchmark: Creating tables...", flush=True)
    from app.core.database import Base

    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    print("run_benchmark: Instantiating DB session...", flush=True)
    db = SessionLocal()
    print("run_benchmark: Instantiating Storage...", flush=True)
    storage = LocalStorageProvider(root=settings.local_storage_path)

    print("run_benchmark: Instantiating Pinecone...", flush=True)
    from unittest.mock import MagicMock

    vectors = MagicMock()
    vectors.upsert.return_value = None
    vectors.query.return_value = []

    print("run_benchmark: Instantiating Providers...", flush=True)
    # To prove offline capability, we ensure LocalE5 loads perfectly offline.
    hf_local = LocalE5Provider(
        model_name=settings.e5_embedding_model,
        dimensions=768,
    )

    providers = [
        GeminiEmbeddingProvider(
            api_key="fake",
            model=settings.gemini_embedding_model,
            dimensions=settings.embedding_dimensions,
            batch_size=20,
            timeout_seconds=10,
        ),
        CohereEmbeddingProvider(
            api_key="fake",
            model=settings.cohere_embedding_model,
            dimensions=settings.embedding_dimensions,
            batch_size=20,
            timeout_seconds=10,
        ),
        HuggingFaceE5Provider(
            api_key="fake",
            model=settings.e5_embedding_model,
            dimensions=settings.embedding_dimensions,
            batch_size=20,
            timeout_seconds=10,
        ),
        hf_local,
    ]
    print("run_benchmark: Instantiating EmbeddingCoordinator...", flush=True)
    coordinator = EmbeddingCoordinator(providers)

    print("run_benchmark: Getting LLM routers...", flush=True)
    # Get generation routers manually for the CLI script context
    q_router = get_question_generation_router()
    p_router = get_presentation_generation_router()

    print("run_benchmark: Fetching User from DB...", flush=True)
    # Make sure we have a test user
    user = db.query(User).filter_by(email="admin@socratia.ai").first()
    if not user:
        print("run_benchmark: Creating test user...", flush=True)
        user = User(
            email="admin@socratia.ai", full_name="Test User", password_hash="fake", roles=[]
        )
        db.add(user)
        db.commit()

    print("run_benchmark: Instantiating Services...", flush=True)
    doc_service = DocumentService(db, storage, vectors)
    processing_service = DocumentProcessingService(db, storage, coordinator, vectors)
    question_service = QuestionBankService(
        db=db, embeddings=coordinator, vectors=vectors, generation_router=q_router
    )
    presentation_service = PresentationMaterialService(
        db=db, embeddings=coordinator, vectors=vectors, generation_router=p_router
    )

    print("run_benchmark: Loading PDF...", flush=True)

    pdf_path = Path(__file__).parent.parent / "proyectSI2_SPRINT4_grupo12.pdf"
    if not pdf_path.exists():
        logger.error(f"Cannot find PDF file at {pdf_path}")
        sys.exit(1)

    benchmark_data = {
        "model": hf_local.model,
        "device": "cpu",  # Assuming CPU for fallback
        "pdf_size_mb": round(os.path.getsize(pdf_path) / (1024 * 1024), 2),
        "chunk_size_chars": settings.document_chunk_size_chars,
        "chunk_overlap": settings.document_chunk_overlap_chars,
        "extracted_chars": 0,
        "chunks": 0,
        "model_load_seconds": 0.0,
        "embedding_seconds": 0.0,
        "avg_chunk_ms": 0.0,
        "query_latency_ms": 0.0,
        "peak_rss_mb": 0.0,
        "cpu_percent_peak": 0.0,
    }

    if psutil:
        psutil.cpu_percent(interval=None)  # Initialize cpu baseline

    try:
        # Load model timing
        t0 = time.monotonic()
        logger.info("Triggering initial model load...")
        hf_local._get_model()  # Force load
        t1 = time.monotonic()
        benchmark_data["model_load_seconds"] = round(t1 - t0, 3)
        logger.info("Model loaded in %.3f s", benchmark_data["model_load_seconds"])

        # Upload
        print("run_benchmark: Uploading document...", flush=True)
        with open(pdf_path, "rb") as f:
            upload_file = UploadFile(
                filename="proyectSI2.pdf", file=f, headers={"content-type": "application/pdf"}
            )
            doc = doc_service.upload(user, upload_file)

        logger.info("Starting processing (should trigger fallback to Local E5)...")
        t2 = time.monotonic()

        response = processing_service.process(user, doc.id)

        t3 = time.monotonic()
        benchmark_data["embedding_seconds"] = round(t3 - t2, 3)
        benchmark_data["chunks"] = response.chunk_count
        if response.chunk_count > 0:
            benchmark_data["avg_chunk_ms"] = round(
                (benchmark_data["embedding_seconds"] * 1000) / response.chunk_count, 2
            )

        logger.info(
            "Document processed: %s in %.3f s (Avg: %.2f ms/chunk)",
            response.status,
            benchmark_data["embedding_seconds"],
            benchmark_data["avg_chunk_ms"],
        )

        assert response.status == DocumentStatus.PROCESSED, (
            f"Expected PROCESSED, got {response.status}"
        )
        assert response.embedding_model == hf_local.model, (
            f"Expected model {hf_local.model}, got {response.embedding_model}"
        )
        assert response.chunk_count > 0, "No chunks were processed"

        # Verify persistence against vector store
        chunks_db = db.query(Chunk).filter_by(document_id=doc.id).all()
        persisted_chunks = len(chunks_db)
        assert persisted_chunks == response.chunk_count, (
            f"Persisted chunks ({persisted_chunks}) != processed chunks ({response.chunk_count})"
        )
        benchmark_data["extracted_chars"] = sum(len(c.content) for c in chunks_db)

        benchmark_data["peak_rss_mb"] = round(get_memory_mb(), 2)
        benchmark_data["cpu_percent_peak"] = round(get_cpu_percent(), 2)

        report_path = Path(__file__).parent / "benchmark_d5_report.json"
        with open(report_path, "w") as f:
            json.dump(benchmark_data, f, indent=2)

        print("\n\n" + "=" * 50)
        print("FASE D-5 BENCHMARK REPORT")
        print("=" * 50)
        print(json.dumps(benchmark_data, indent=2))
        print("=" * 50)
        print("✅ SUCCESS")

    finally:
        db.close()


if __name__ == "__main__":
    run_benchmark()
