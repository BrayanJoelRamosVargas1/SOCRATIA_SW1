from app.core.database import get_db
from fastapi import Depends
from sqlalchemy.orm import Session

from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.embeddings.dependencies import get_embedding_provider
from app.integrations.retrieval.lexical import PostgresLexicalFallbackRetriever
from app.integrations.retrieval.router import RetrievalRouter
from app.integrations.vector_db.base import VectorStoreProvider
from app.integrations.vector_db.dependencies import get_vector_store_provider


def get_retrieval_router(
    db: Session = Depends(get_db),
    embeddings: EmbeddingProvider = Depends(get_embedding_provider),
    vector_router: VectorStoreProvider = Depends(get_vector_store_provider),
) -> RetrievalRouter:
    lexical_retriever = PostgresLexicalFallbackRetriever(db)

    # The vector_router is expected to be a VectorStoreRouter (from get_vector_store_provider)
    return RetrievalRouter(
        embeddings=embeddings, vector_router=vector_router, lexical_retriever=lexical_retriever
    )
