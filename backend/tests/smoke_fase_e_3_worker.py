import os
import sys
import time
import uuid

# Add backend dir to sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.document import (
    ChunkSet,
    Document,
    DocumentChunk,
    DocumentStatus,
    EmbeddingProfile,
    ProfileStatus,
)
from app.modules.p2_gestion_documentos_preparacion.models.vector_store import (
    EmbeddingProfileStoreSync,
    VectorSyncOutbox,
)


def test_worker_durable_sync():
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email="smoke-test@example.com").first()
        if not user:
            user = User(email="smoke-test@example.com", full_name="Smoke Test", password_hash="xxx")
            db.add(user)
            db.commit()
            db.refresh(user)

        # 1. Setup minimal document structure
        doc = Document(
            user_id=user.id,
            original_name="smoke_e3.pdf",
            file_type="PDF",
            file_size=123,
            content_hash=uuid.uuid4().hex,
            storage_key=f"mock/key/{uuid.uuid4().hex}.pdf",
            status=DocumentStatus.PROCESSED,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        chunk_set = ChunkSet(
            document_id=doc.id,
            fingerprint=uuid.uuid4().hex,
            chunk_size_chars=3000,
            chunk_overlap_chars=400,
            extractor_version="1.0",
            normalization_version="1.0",
            chunker_version="1.0",
        )
        db.add(chunk_set)
        db.commit()
        db.refresh(chunk_set)

        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_set_id=chunk_set.id,
            chunk_index=0,
            content="Smoke test content for worker",
            start_char=0,
            end_char=20,
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)

        profile = EmbeddingProfile(
            document_id=doc.id,
            chunk_set_id=chunk_set.id,
            status=ProfileStatus.STAGING,
            embedding_space_id="test_space",
            provider="gemini",
            model="gemini-embedding-2",
            dimension=768,
            vector_index="socratia-documents",
            vector_namespace=f"socratia-{uuid.uuid4().hex[:8]}",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        from sqlalchemy import text

        vec_id = str(uuid.uuid4())
        db.execute(
            text("""
            INSERT INTO vector_embeddings_768 (id, profile_id, chunk_id, document_id, user_id, embedding_space_id, embedding) 
            VALUES (:id, :profile_id, :chunk_id, :document_id, :user_id, :embedding_space_id, CAST(:embedding AS vector))
        """),
            {
                "id": vec_id,
                "profile_id": profile.id,
                "chunk_id": chunk.id,
                "document_id": doc.id,
                "user_id": user.id,
                "embedding_space_id": profile.embedding_space_id,
                "embedding": str([0.1] * 768),
            },
        )

        store_sync = EmbeddingProfileStoreSync(
            profile_id=profile.id,
            store_name="pinecone",
            status="PENDING",
            vectors_expected=1,
            vectors_synced=0,
        )
        db.add(store_sync)

        outbox = VectorSyncOutbox(
            profile_id=profile.id,
            chunk_id=chunk.id,
            dimension=768,
            operation="UPSERT",
            status="PENDING",
        )
        db.add(outbox)
        db.commit()

        print(f"Created outbox {outbox.id} for profile {profile.id}")

        # 3. Wait for the worker to process it
        max_waits = 30
        for i in range(max_waits):
            db.refresh(outbox)
            if outbox.status == "COMPLETED" or outbox.status == "ERROR":
                break
            time.sleep(1)

        print(f"Outbox status after waiting: {outbox.status}")

        db.refresh(store_sync)
        print(f"StoreSync status: {store_sync.status}, synced: {store_sync.vectors_synced}")

        assert outbox.status == "COMPLETED"
        assert store_sync.status == "SYNCED"
        assert store_sync.vectors_synced == 1

    finally:
        db.close()


if __name__ == "__main__":
    test_worker_durable_sync()
