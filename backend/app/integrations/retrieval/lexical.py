from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.retrieval.base import RetrievalMode, RetrievalResult


class PostgresLexicalFallbackRetriever:
    """
    Implements Graceful Degradation using PostgreSQL Full-Text Search (FTS).
    Used as the absolute last resort when vector stores or embedding providers are unavailable.
    """

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def search(
        self, document_id: str, user_id: str, chunk_set_id: str, query_text: str, top_k: int = 4
    ) -> list[RetrievalResult]:

        # Ensure we don't return 500 on empty queries
        if not query_text or not query_text.strip():
            return []

        sql = text("""
            SELECT 
                c.id, 
                c.content, 
                ts_rank_cd(c.search_vector, websearch_to_tsquery(:config, :query_text)) AS rank_score
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.document_id = :document_id
              AND c.chunk_set_id = :chunk_set_id
              AND d.user_id = :user_id
              AND c.search_vector @@ websearch_to_tsquery(:config, :query_text)
            ORDER BY rank_score DESC
            LIMIT :top_k
        """)

        results = self.db.execute(
            sql,
            {
                "config": self.settings.fts_default_config,
                "query_text": query_text,
                "document_id": document_id,
                "chunk_set_id": chunk_set_id,
                "user_id": user_id,
                "top_k": top_k,
            },
        ).fetchall()

        if not results:
            # When lexical keyword match yields 0 rows (e.g. language mismatch or synthetic documents),
            # provide the first top_k chunks of the document so degraded mode doesn't starve downstream LLM.
            fallback_sql = text("""
                SELECT 
                    c.id, 
                    c.content, 
                    0.001 AS rank_score
                FROM document_chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.document_id = :document_id
                  AND c.chunk_set_id = :chunk_set_id
                  AND d.user_id = :user_id
                ORDER BY c.chunk_index ASC
                LIMIT :top_k
            """)
            results = self.db.execute(
                fallback_sql,
                {
                    "document_id": document_id,
                    "chunk_set_id": chunk_set_id,
                    "user_id": user_id,
                    "top_k": top_k,
                },
            ).fetchall()

        retrieval_results = []
        for rank_idx, row in enumerate(results, start=1):
            retrieval_results.append(
                RetrievalResult(
                    chunk_id=row.id,
                    content=row.content,
                    rank=rank_idx,
                    raw_score=float(row.rank_score),
                    retrieval_mode=RetrievalMode.LEXICAL_FALLBACK,
                    source="postgres_fts",
                    degraded=True,
                )
            )

        return retrieval_results
