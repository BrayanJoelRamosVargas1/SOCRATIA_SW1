import logging

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.integrations.embeddings.gemini import GeminiEmbeddingProvider
from app.integrations.storage.local import LocalStorageProvider
from app.integrations.vector_db.pinecone import PineconeVectorStoreProvider
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.services.document_processing_service import (
    DocumentProcessingService,
)

logging.basicConfig(level=logging.INFO)
settings = get_settings()

db = SessionLocal()

# Set to ERROR so it can be re-processed
db.execute(
    text("UPDATE documents SET status = 'ERROR' WHERE id = '810e7c2a-6eb0-4919-9459-73349af6b7ae'")
)
db.commit()

user = db.query(User).filter_by(id="16d34298-3bf3-4b25-b142-1b9bc8590072").first()

storage = LocalStorageProvider(root=settings.local_storage_path)
embeddings = GeminiEmbeddingProvider(
    api_key=settings.gemini_api_key.get_secret_value(),
    model=settings.gemini_embedding_model,
    dimensions=settings.embedding_dimensions,
    batch_size=settings.embedding_batch_size,
    timeout_seconds=settings.embedding_timeout_seconds,
)
vectors = PineconeVectorStoreProvider(
    api_key=settings.pinecone_api_key.get_secret_value(),
    index_name=settings.pinecone_index_name,
    dimensions=settings.embedding_dimensions,
    cloud=settings.pinecone_cloud,
    region=settings.pinecone_region,
    timeout_seconds=settings.pinecone_timeout_seconds,
)

service = DocumentProcessingService(
    db=db,
    storage=storage,
    embeddings=embeddings,
    vectors=vectors,
)

print("Starting processing for PDF...")
try:
    response = service.process(user, "810e7c2a-6eb0-4919-9459-73349af6b7ae")
    print("Finished processing!", response.status)
except Exception as e:
    print("Failed!", e)
