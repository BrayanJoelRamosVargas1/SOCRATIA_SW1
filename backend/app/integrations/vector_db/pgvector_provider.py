from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.vector_db.base import (
    VectorFilter,
    VectorRecord,
    VectorSearchResult,
    VectorStoreError,
    VectorStoreProvider,
)


class PgVectorStoreProvider(VectorStoreProvider):
    def __init__(self, db: Session):
        self.db = db

    def upsert(
        self,
        *,
        namespace: str,
        records: list[VectorRecord],
        index_name: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        """PgVectorStoreProvider shouldn't normally be called for upsert by the Router directly,
        because outbox manages it, but we implement it as no-op or pass."""
        pass

    def delete(self, *, namespace: str, ids: list[str], index_name: str | None = None) -> None:
        pass

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
        if not dimensions:
            raise VectorStoreError("Dimensions must be provided for PgVectorStoreProvider")
        document_id = filters.get("document_id")
        user_id = filters.get("user_id")

        if "$and" in filters:
            for f in filters["$and"]:
                if "document_id" in f:
                    document_id = (
                        f["document_id"].get("$eq", f["document_id"])
                        if isinstance(f["document_id"], dict)
                        else f["document_id"]
                    )
                if "user_id" in f:
                    user_id = (
                        f["user_id"].get("$eq", f["user_id"])
                        if isinstance(f["user_id"], dict)
                        else f["user_id"]
                    )

        if not document_id or not user_id:
            raise VectorStoreError("document_id and user_id are required in filters")

        # Select table based on dimension
        table_name = f"vector_embeddings_{dimensions}"
        if dimensions not in (768, 1024):
            raise VectorStoreError(f"Unsupported dimension for pgvector: {dimensions}")

        # Format vector as pgvector string
        vector_str = "[" + ",".join(str(v) for v in vector) + "]"

        # Note: In postgres, embedding <=> query returns the cosine DISTANCE.
        # We want cosine SIMILARITY, which is 1 - distance.
        sql = text(f"""
            SELECT 
                ve.chunk_id,
                dc.content,
                1 - (ve.embedding::vector <=> :vector) as score,
                dc.chunk_index
            FROM {table_name} ve
            JOIN document_chunks dc ON ve.chunk_id = dc.id
            WHERE ve.profile_id = :profile_id
              AND ve.document_id = :document_id
              AND ve.user_id = :user_id
            ORDER BY ve.embedding::vector <=> :vector
            LIMIT :top_k
        """)

        try:
            result = self.db.execute(
                sql,
                {
                    "vector": vector_str,
                    "profile_id": profile_id,
                    "document_id": document_id,
                    "user_id": user_id,
                    "top_k": top_k,
                },
            ).fetchall()
        except Exception as e:
            raise VectorStoreError(f"Failed to query pgvector: {str(e)}") from e

        matches = []
        for row in result:
            matches.append(
                VectorSearchResult(
                    chunk_id=row.chunk_id,
                    content=row.content,
                    score=float(row.score),
                    metadata={
                        "user_id": user_id,
                        "document_id": document_id,
                        "chunk_index": row.chunk_index,
                        "text": row.content,
                    },
                    source_store="pgvector",
                )
            )
        return matches
