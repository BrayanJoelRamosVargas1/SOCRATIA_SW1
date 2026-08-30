import time
from collections.abc import Iterable

import httpx

from app.integrations.vector_db.base import (
    VectorFilter,
    VectorMatch,
    VectorRecord,
    VectorStoreError,
)

PINECONE_CONTROL_URL = "https://api.pinecone.io"
PINECONE_API_VERSION = "2025-10"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class PineconeVectorStoreProvider:
    """Pinecone serverless adapter for Gemini-generated dense vectors."""

    def __init__(
        self,
        *,
        api_key: str | None,
        index_name: str,
        dimensions: int,
        cloud: str,
        region: str,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self.index_name = index_name
        self.dimensions = dimensions
        self.cloud = cloud
        self.region = region
        self.timeout_seconds = timeout_seconds
        self._host: str | None = None

    def upsert(self, *, namespace: str, records: list[VectorRecord]) -> None:
        if not records:
            return
        if any(len(record.values) != self.dimensions for record in records):
            raise VectorStoreError("Vector dimensions do not match the Pinecone index")
        host = self._ensure_index()
        with self._client() as client:
            for batch in self._batches(records, 100):
                payload = {
                    "vectors": [
                        {
                            "id": record.id,
                            "values": record.values,
                            "metadata": record.metadata,
                        }
                        for record in batch
                    ],
                    "namespace": namespace,
                }
                self._request(client, "POST", f"https://{host}/vectors/upsert", json=payload)

    def delete(self, *, namespace: str, ids: list[str]) -> None:
        if not ids:
            return
        host = self._ensure_index()
        with self._client() as client:
            for batch in self._batches(ids, 1000):
                self._request(
                    client,
                    "POST",
                    f"https://{host}/vectors/delete",
                    json={"ids": batch, "namespace": namespace},
                )

    def query(
        self,
        *,
        namespace: str,
        vector: list[float],
        top_k: int,
        filters: VectorFilter,
    ) -> list[VectorMatch]:
        if len(vector) != self.dimensions:
            raise VectorStoreError("Query dimensions do not match the Pinecone index")
        if not filters:
            raise VectorStoreError("Pinecone queries require metadata filters")
        host = self._ensure_index()
        with self._client() as client:
            response = self._request(
                client,
                "POST",
                f"https://{host}/query",
                json={
                    "namespace": namespace,
                    "vector": vector,
                    "topK": top_k,
                    "filter": filters,
                    "includeMetadata": True,
                    "includeValues": False,
                },
            )
        body = self._json_object(response)
        raw_matches = body.get("matches")
        if not isinstance(raw_matches, list):
            raise VectorStoreError("Pinecone returned invalid query matches")

        matches: list[VectorMatch] = []
        for raw_match in raw_matches:
            if not isinstance(raw_match, dict):
                raise VectorStoreError("Pinecone returned an invalid query match")
            match_id = raw_match.get("id")
            score = raw_match.get("score")
            metadata = raw_match.get("metadata", {})
            if not isinstance(match_id, str) or not isinstance(score, (int, float)):
                raise VectorStoreError("Pinecone returned an invalid query match")
            if not isinstance(metadata, dict):
                raise VectorStoreError("Pinecone returned invalid match metadata")
            matches.append(
                VectorMatch(
                    id=match_id,
                    score=float(score),
                    metadata={str(key): value for key, value in metadata.items()},
                )
            )
        return matches

    def _ensure_index(self) -> str:
        if self._host:
            return self._host
        if not self.api_key:
            raise VectorStoreError("Pinecone is not configured")

        with self._client() as client:
            response = self._request(
                client,
                "GET",
                f"{PINECONE_CONTROL_URL}/indexes/{self.index_name}",
                allowed_status_codes={404},
            )
            if response.status_code == 404:
                response = self._request(
                    client,
                    "POST",
                    f"{PINECONE_CONTROL_URL}/indexes",
                    json={
                        "name": self.index_name,
                        "vector_type": "dense",
                        "dimension": self.dimensions,
                        "metric": "cosine",
                        "spec": {
                            "serverless": {"cloud": self.cloud, "region": self.region}
                        },
                        "deletion_protection": "disabled",
                        "tags": {"application": "socratia"},
                    },
                )

            description = self._json_object(response)
            self._validate_index(description)
            deadline = time.monotonic() + self.timeout_seconds
            while not self._is_ready(description):
                if time.monotonic() >= deadline:
                    raise VectorStoreError("Pinecone index did not become ready in time")
                time.sleep(1)
                response = self._request(
                    client,
                    "GET",
                    f"{PINECONE_CONTROL_URL}/indexes/{self.index_name}",
                )
                description = self._json_object(response)

        host = description.get("host")
        if not isinstance(host, str) or not host:
            raise VectorStoreError("Pinecone did not return an index host")
        self._host = host
        return host

    def _validate_index(self, description: dict[str, object]) -> None:
        dimension = description.get("dimension")
        metric = description.get("metric")
        if dimension != self.dimensions or metric != "cosine":
            raise VectorStoreError(
                "Existing Pinecone index does not match configured dimensions and metric"
            )

    @staticmethod
    def _is_ready(description: dict[str, object]) -> bool:
        status = description.get("status")
        return isinstance(status, dict) and status.get("ready") is True

    def _client(self) -> httpx.Client:
        if not self.api_key:
            raise VectorStoreError("Pinecone is not configured")
        return httpx.Client(
            headers={
                "Api-Key": self.api_key,
                "Content-Type": "application/json",
                "X-Pinecone-Api-Version": PINECONE_API_VERSION,
            },
            timeout=self.timeout_seconds,
        )

    @staticmethod
    def _json_object(response: httpx.Response) -> dict[str, object]:
        try:
            body = response.json()
        except ValueError as exc:
            raise VectorStoreError("Pinecone returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise VectorStoreError("Pinecone returned an invalid response")
        return body

    @staticmethod
    def _request(
        client: httpx.Client,
        method: str,
        url: str,
        *,
        json: dict[str, object] | None = None,
        allowed_status_codes: set[int] | None = None,
    ) -> httpx.Response:
        allowed = allowed_status_codes or set()
        for attempt in range(3):
            try:
                response = client.request(method, url, json=json)
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise VectorStoreError("Pinecone could not be reached") from exc
                time.sleep(2**attempt)
                continue
            if response.status_code in RETRYABLE_STATUS_CODES and attempt < 2:
                time.sleep(2**attempt)
                continue
            if response.is_error and response.status_code not in allowed:
                raise VectorStoreError(
                    f"Pinecone rejected the request ({response.status_code})"
                )
            return response
        raise VectorStoreError("Pinecone could not complete the request")

    @staticmethod
    def _batches(items: list, batch_size: int) -> Iterable[list]:
        for start in range(0, len(items), batch_size):
            yield items[start : start + batch_size]
