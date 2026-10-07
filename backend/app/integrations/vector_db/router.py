import logging
import os
import time
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.vector_db.base import (
    VectorFilter,
    VectorRecord,
    VectorSearchResult,
    VectorStoreError,
    VectorStoreProvider,
)
from app.modules.p2_gestion_documentos_preparacion.models.document import EmbeddingProfile
from app.modules.p2_gestion_documentos_preparacion.models.vector_store import (
    EmbeddingProfileStoreSync,
)

logger = logging.getLogger(__name__)

# Configurable CB values (defaults matching the old hardcodes)
CB_FAILURE_THRESHOLD = int(os.environ.get("VECTOR_STORE_CB_FAILURE_THRESHOLD", "3"))
CB_OPEN_SECONDS = int(os.environ.get("VECTOR_STORE_CB_OPEN_SECONDS", "30"))


class VectorStoreRouter(VectorStoreProvider):
    def __init__(
        self,
        primary: VectorStoreProvider,
        secondary: VectorStoreProvider,
        db: Session,
        circuit_breaker_timeout_sec: int = CB_OPEN_SECONDS,
        circuit_breaker_failure_threshold: int = CB_FAILURE_THRESHOLD,
    ):
        self.primary = primary
        self.secondary = secondary
        self.db = db
        self.circuit_breaker_timeout_sec = circuit_breaker_timeout_sec
        self.circuit_breaker_failure_threshold = circuit_breaker_failure_threshold

        self._circuit_open_until: float | None = None
        self._consecutive_failures = 0
        self._state: Literal["CLOSED", "OPEN", "HALF_OPEN"] = "CLOSED"

    def _get_circuit_state(self) -> Literal["CLOSED", "OPEN", "HALF_OPEN"]:
        if self._state == "OPEN":
            if time.monotonic() >= self._circuit_open_until:
                self._state = "HALF_OPEN"
                logger.info("VectorStoreRouter circuit breaker HALF-OPEN (probe)")
        return self._state

    def _record_success(self):
        if self._state != "CLOSED":
            logger.info("VectorStoreRouter circuit breaker CLOSED (recovered)")
            self._state = "CLOSED"
        self._consecutive_failures = 0
        self._circuit_open_until = None

    def _record_failure(self):
        self._consecutive_failures += 1
        if (
            self._state == "HALF_OPEN"
            or self._consecutive_failures >= self.circuit_breaker_failure_threshold
        ):
            self._state = "OPEN"
            self._circuit_open_until = time.monotonic() + self.circuit_breaker_timeout_sec
            logger.warning(
                f"VectorStoreRouter circuit breaker OPENED for {self.circuit_breaker_timeout_sec}s"
            )

    def upsert(
        self,
        *,
        namespace: str,
        records: list[VectorRecord],
        index_name: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        """
        As instructed, VectorStoreRouter is for READ ROUTING.
        Writes (upsert/delete) are handled exclusively by the Outbox worker.
        """
        raise NotImplementedError(
            "VectorStoreRouter is for retrieval only. Use Transactional Outbox for writes."
        )

    def delete(self, *, namespace: str, ids: list[str], index_name: str | None = None) -> None:
        self.primary.delete(namespace=namespace, ids=ids, index_name=index_name)
        # pgvector delete is usually handled by CASCADE on document delete, but we pass it anyway
        self.secondary.delete(namespace=namespace, ids=ids, index_name=index_name)

    def query(
        self,
        *,
        profile_id: str,
        namespace: str,
        vector: list[float],
        top_k: int,
        filters: VectorFilter,
        index_name: str | None = None,
        dimensions: int | None = None,
    ) -> list[VectorSearchResult]:

        t0 = time.monotonic()
        primary_latency = 0.0

        # Verify Dimension from EmbeddingProfile
        profile = self.db.execute(
            select(EmbeddingProfile).where(EmbeddingProfile.id == profile_id)
        ).first()
        profile = profile[0] if profile else None

        if not profile:
            raise VectorStoreError(f"EmbeddingProfile {profile_id} not found.")

        expected_dim = profile.dimension
        if dimensions is not None and dimensions != expected_dim:
            logger.warning(
                f"Query dimensions {dimensions} do not match profile {expected_dim}. Using profile dimension."
            )
        if len(vector) != expected_dim:
            raise VectorStoreError(
                f"Vector length {len(vector)} does not match profile dimension {expected_dim}"
            )

        dimensions = expected_dim

        cb_state = self._get_circuit_state()

        # 1. Attempt Primary if circuit is not fully open
        if cb_state in ("CLOSED", "HALF_OPEN"):
            try:
                results = self.primary.query(
                    profile_id=profile_id,
                    namespace=namespace,
                    vector=vector,
                    top_k=top_k,
                    filters=filters,
                    index_name=index_name,
                    dimensions=dimensions,
                )
                primary_latency = (time.monotonic() - t0) * 1000
                self._record_success()

                self._record_telemetry(
                    profile_id=profile_id,
                    primary_used=True,
                    fallback_used=False,
                    primary_latency_ms=primary_latency,
                    secondary_latency_ms=0.0,
                    result_count=len(results),
                    fallback_reason=None,
                )
                return results

            except VectorStoreError as e:
                err_str = str(e).lower()
                primary_latency = (time.monotonic() - t0) * 1000

                if "400" in err_str or "422" in err_str:
                    logger.error(
                        f"Pinecone invalid request (400/422): {str(e)} - Not opening circuit"
                    )
                    # Reraise as ValueError so it can bypass generic fallback if we want, or just let it be handled
                    # but importantly, we DO NOT call self._record_failure()
                    raise ValueError(f"Invalid request to vector store: {str(e)}") from e
                elif "401" in err_str or "403" in err_str or "unauthorized" in err_str:
                    logger.error(f"PINECONE_AUTH_FAILURE: {str(e)} - Falling back to pgvector")
                    fallback_reason = "PINECONE_AUTH_FAILURE"
                else:
                    logger.warning(f"Pinecone query failed: {str(e)} - Registering failure")
                    self._record_failure()
                    fallback_reason = "PRIMARY_UNAVAILABLE"
            except Exception as e:
                err_str = str(type(e)).lower() + " " + str(e).lower()

                if "timeout" in err_str or "connect" in err_str or "network" in err_str:
                    logger.warning(f"Pinecone operational error: {str(e)} - Registering failure")
                    self._record_failure()
                    fallback_reason = "PRIMARY_NETWORK_ERROR"
                    primary_latency = (time.monotonic() - t0) * 1000
                else:
                    # Programming errors -> DO NOT fallback silently
                    raise ValueError(f"Programming error in vector store: {str(e)}") from e
        else:
            logger.info("Pinecone circuit is OPEN. Routing directly to pgvector")
            fallback_reason = "CIRCUIT_OPEN"

        # 2. Check if pgvector is fully synced before allowing fallback
        if not self._is_pgvector_synced(profile_id):
            logger.error(f"Fallback aborted: pgvector is not SYNCED for profile {profile_id}")
            raise VectorStoreError(
                "Primary store unavailable and Secondary store is not completely SYNCED"
            )

        t1 = time.monotonic()
        try:
            results = self.secondary.query(
                profile_id=profile_id,
                namespace=namespace,
                vector=vector,
                top_k=top_k,
                filters=filters,
                index_name=index_name,
                dimensions=dimensions,
            )
            secondary_latency = (time.monotonic() - t1) * 1000
            self._record_telemetry(
                profile_id=namespace,
                primary_used=False,
                fallback_used=True,
                primary_latency_ms=primary_latency,
                secondary_latency_ms=secondary_latency,
                result_count=len(results),
                fallback_reason=fallback_reason,
            )
            return results
        except Exception as e:
            logger.error(f"Secondary pgvector also failed during fallback: {str(e)}")
            raise VectorStoreError(
                f"Both primary and secondary vector stores failed. Secondary error: {str(e)}"
            ) from e

    def _is_pgvector_synced(self, namespace: str) -> bool:
        profile_id = namespace.split("-p-")[-1] if "-p-" in namespace else namespace
        sync_state = self.db.execute(
            select(EmbeddingProfileStoreSync).where(
                EmbeddingProfileStoreSync.profile_id == profile_id,
                EmbeddingProfileStoreSync.store_name == "pgvector",
            )
        ).scalar_one_or_none()

        if not sync_state:
            return False

        return sync_state.status == "SYNCED"

    def _record_telemetry(
        self,
        *,
        profile_id: str,
        primary_used: bool,
        fallback_used: bool,
        primary_latency_ms: float,
        secondary_latency_ms: float,
        result_count: int,
        fallback_reason: str | None,
    ):
        logger.info(
            f"[VECTOR_TELEMETRY] profile={profile_id} "
            f"primary={primary_used} fallback={fallback_used} "
            f"primary_ms={primary_latency_ms:.2f} secondary_ms={secondary_latency_ms:.2f} "
            f"results={result_count} reason={fallback_reason}"
        )
