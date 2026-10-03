import json
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.integrations.vector_db.base import VectorRecord
from app.integrations.vector_db.pinecone import PineconeVectorStoreProvider
from app.modules.p2_gestion_documentos_preparacion.models.document import EmbeddingProfile
from app.modules.p2_gestion_documentos_preparacion.models.vector_store import (
    EmbeddingProfileStoreSync,
    VectorEmbedding768,
    VectorEmbedding1024,
    VectorSyncOutbox,
)

logger = logging.getLogger(__name__)

# Constants
BATCH_SIZE = 50
MAX_ATTEMPTS = 5
LEASE_DURATION_SECONDS = 60
BASE_BACKOFF_SECONDS = 5


def init_pinecone() -> PineconeVectorStoreProvider:
    settings = get_settings()
    if not settings.pinecone_api_key:
        logger.warning("Pinecone API key not configured, worker will fail if it attempts to sync.")
    api_key = (
        settings.pinecone_api_key.get_secret_value()
        if hasattr(settings.pinecone_api_key, "get_secret_value")
        else settings.pinecone_api_key
    )
    return PineconeVectorStoreProvider(
        api_key=api_key,
        index_name=settings.pinecone_index_name,
        dimensions=settings.embedding_dimensions,
        cloud=settings.pinecone_cloud,
        region=settings.pinecone_region,
        timeout_seconds=30,
    )


def fetch_and_lock_batch(db: Session, worker_id: str) -> list[VectorSyncOutbox]:
    now = datetime.now(UTC)

    # We want to select PENDING items or items that are RETRYING where next_retry_at is reached
    # or items that were locked but the lease expired.
    stmt = (
        select(VectorSyncOutbox)
        .where(
            (VectorSyncOutbox.status.in_(["PENDING", "RETRYING"]))
            & ((VectorSyncOutbox.next_retry_at == None) | (VectorSyncOutbox.next_retry_at <= now))
            & (
                (VectorSyncOutbox.lease_expires_at == None)
                | (VectorSyncOutbox.lease_expires_at <= now)
            )
        )
        .limit(BATCH_SIZE)
        .with_for_update(skip_locked=True)
    )

    records = db.execute(stmt).scalars().all()

    if not records:
        return []

    # Update lease
    lease_expires = now + timedelta(seconds=LEASE_DURATION_SECONDS)
    for record in records:
        record.locked_at = now
        record.locked_by = worker_id
        record.lease_expires_at = lease_expires

    db.commit()
    return list(records)


def process_batch(db: Session, store: PineconeVectorStoreProvider, records: list[VectorSyncOutbox]):
    now = datetime.now(UTC)

    upsert_groups = {}

    for item in records:
        if item.operation == "DELETE":
            if item.target_namespace:
                try:
                    store.delete_namespace(namespace=item.target_namespace, index_name=item.target_index)
                    item.status = "COMPLETED"
                except Exception:
                    item.attempts += 1
                    if item.attempts >= 5:
                        item.status = "ERROR"
                    else:
                        item.status = "RETRYING"
                        item.next_retry_at = now + timedelta(seconds=(2 ** item.attempts) * 5)
            else:
                item.status = "ERROR"
            continue

        if item.operation != "UPSERT":
            continue

        if item.dimension == 768:
            vec_model = VectorEmbedding768
        elif item.dimension == 1024:
            vec_model = VectorEmbedding1024
        else:
            item.status = "ERROR"
            continue

        vec = db.execute(
            select(vec_model).where(
                vec_model.profile_id == item.profile_id, vec_model.chunk_id == item.chunk_id
            )
        ).scalar_one_or_none()

        if not vec:
            item.status = "ERROR"
            continue

        try:
            values = json.loads(vec.embedding) if isinstance(vec.embedding, str) else vec.embedding
        except Exception:
            try:
                values = [float(x) for x in vec.embedding.strip("[]").split(",")]
            except Exception:
                item.status = "ERROR"
                continue

        pinecone_id = f"{item.profile_id}:{item.chunk_id}"
        record = VectorRecord(
            id=pinecone_id,
            values=values,
            metadata={
                "document_id": vec.document_id,
                "profile_id": vec.profile_id,
                "chunk_id": vec.chunk_id,
                "user_id": vec.user_id,
            },
        )

        profile = db.execute(
            select(EmbeddingProfile).where(EmbeddingProfile.id == item.profile_id)
        ).scalar_one_or_none()
        if not profile:
            item.status = "ERROR"
            continue

        namespace = profile.vector_namespace

        key = (item.profile_id, namespace, item.dimension)
        if key not in upsert_groups:
            upsert_groups[key] = []
        upsert_groups[key].append((item, record))

    # Perform Upserts
    for (profile_id, namespace, dimension), group in upsert_groups.items():
        items = [g[0] for g in group]
        records_to_upsert = [g[1] for g in group]

        try:
            store.upsert(namespace=namespace, records=records_to_upsert, dimensions=dimension)
            for item in items:
                item.status = "COMPLETED"

            sync = db.execute(
                select(EmbeddingProfileStoreSync)
                .where(
                    EmbeddingProfileStoreSync.profile_id == profile_id,
                    EmbeddingProfileStoreSync.store_name == "pinecone",
                )
                .with_for_update()
            ).scalar_one_or_none()

            if sync:
                sync.vectors_synced += len(items)
                sync.last_synced_at = now
                if sync.vectors_synced >= sync.vectors_expected:
                    sync.status = "SYNCED"
                else:
                    sync.status = "SYNCING"

        except Exception as e:
            logger.error(f"Failed to upsert to pinecone for profile {profile_id}: {e}")
            for item in items:
                item.attempts += 1
                if item.attempts >= MAX_ATTEMPTS:
                    item.status = "ERROR"
                else:
                    item.status = "RETRYING"
                    delay = BASE_BACKOFF_SECONDS * (2 ** (item.attempts - 1))
                    item.next_retry_at = now + timedelta(seconds=delay)
                item.locked_by = None
                item.locked_at = None
                item.lease_expires_at = None

    for item in records:
        if item.status == "COMPLETED":
            db.delete(item)

    db.commit()


def run_worker():
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    logger.info(f"Starting vector sync worker {worker_id}")
    store = init_pinecone()

    while True:
        db = SessionLocal()
        try:
            records = fetch_and_lock_batch(db, worker_id)
            if records:
                logger.info(f"Worker {worker_id} claimed {len(records)} items")
                process_batch(db, store, records)
            else:
                time.sleep(2)
        except Exception as e:
            logger.error(f"Worker {worker_id} encountered error: {e}", exc_info=True)
            db.rollback()
            time.sleep(5)
        finally:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    run_worker()
