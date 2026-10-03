from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.p2_gestion_documentos_preparacion.repositories.document_repository import (
    DocumentRepository,
)
from tests.test_question_banks import processed_document, register


def test_tenant_isolation_retrieval_service(
    client: TestClient,
    db_session: Session,
    vector_store: Any,
    embedding_provider: Any,
) -> None:
    # 1. User A (owner) uploads and processes document
    document_id_a = processed_document(client, "user-a-owner@example.com")

    # 2. User B (intruder) registers
    register(client, "user-b-intruder@example.com")
    user_b = db_session.execute(
        text("SELECT id FROM users WHERE email = 'user-b-intruder@example.com'")
    ).scalar_one()

    # 3. Obtain the document object
    doc_repo = DocumentRepository(db_session)
    document = doc_repo.get_by_id(document_id_a)
    
    # 4. User B attempts to retrieve via DocumentRetrievalService using document object A!
    # Even if they bypass the initial DocumentPolicy (e.g. knowing document_id_a),
    # the RetrievalRouter.retrieve_for_document will be called with user_id=User B.
    # We want to ensure that vectors are scoped so User B cannot get any results,
    # OR that the service refuses because the Document.user_id doesn't match User B.
    # Let's call retrieve_for_document directly on the router to verify isolation!
    
    from app.integrations.retrieval.lexical import PostgresLexicalFallbackRetriever
    from app.integrations.retrieval.router import RetrievalRouter
    router = RetrievalRouter(
        embeddings=embedding_provider,
        vector_router=vector_store,
        lexical_retriever=PostgresLexicalFallbackRetriever(db_session),
    )
    
    # Call retrieve_for_document with user_id = User B, but document = User A's document
    matches, fallback_reason = router.retrieve_for_document(
        document=document,
        user_id=user_b,
        query_text="Test query",
        top_k=5
    )
    
    # 5. It should return 0 matches because the active_profile belongs to user A, not user B.
    # Wait, the RetrievalRouter.retrieve_for_document will look for a profile for user_b!
    # Since user_b didn't upload this document, user_b has NO profile for document_id_a!
    
    assert len(matches) == 0
    # Wait! Actually, profile will be None!
    # "If active_profile is None -> FTS degraded or just empty."
    # Let's test that the vector router doesn't get queried!
    
    # Actually, FTS would execute. But FTS also searches for document_id and user_b!
    # FTS query uses active_profile or just document_id & user_id. 
    # FTS matches will be 0 because document_id_a doesn't belong to user_b in FTS search (no profile or user mismatch).
