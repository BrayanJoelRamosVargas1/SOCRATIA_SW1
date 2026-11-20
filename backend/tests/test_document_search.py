from unittest.mock import Mock

from app.integrations.retrieval.base import FallbackReason, RetrievalMode, RetrievalResult
from app.integrations.retrieval.dependencies import get_retrieval_router
from app.main import app
from app.modules.p2_gestion_documentos_preparacion.models.document import Document, EmbeddingProfile
from tests.test_documents import register, valid_docx


def processed(client):
    register(client, "search-owner@example.com")
    response = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "tesis.docx",
                valid_docx("La validación experimental comparó dos grupos de estudiantes."),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    document = response.json()
    assert client.post(f"/api/v1/documents/{document['id']}/process").status_code == 200
    return document["id"]


def test_search_rejects_foreign_document_before_inference(client):
    document_id = processed(client)
    register(client, "search-other@example.com")
    retrieval = Mock()
    app.dependency_overrides[get_retrieval_router] = lambda: retrieval
    result = client.post(
        f"/api/v1/documents/{document_id}/search", json={"query": "cómo se validó"}
    )
    assert result.status_code == 404
    retrieval.retrieve_for_document.assert_not_called()


def test_search_returns_canonical_owner_text_and_honest_engine(client, db_session):
    document_id = processed(client)
    from app.modules.p2_gestion_documentos_preparacion.models.document import DocumentChunk

    chunk = db_session.query(DocumentChunk).filter_by(document_id=document_id).first()
    document = db_session.get(Document, document_id)
    profile = db_session.get(EmbeddingProfile, document.active_embedding_profile_id)
    profile.provider = "qwen_local"
    profile.model = "Qwen3-Embedding-0.6B-Q8_0"
    db_session.commit()
    retrieval = Mock()
    result = RetrievalResult(
        chunk.id, "untrusted vector payload", 1, 0.7, RetrievalMode.VECTOR_PRIMARY, "pgvector"
    )
    retrieval.retrieve_for_document.return_value = ([result], FallbackReason.NONE)
    app.dependency_overrides[get_retrieval_router] = lambda: retrieval
    response = client.post(
        f"/api/v1/documents/{document_id}/search", json={"query": "cómo se validó"}
    )
    assert response.status_code == 200
    assert response.json()["engine"] == "qwen_local"
    assert response.json()["matches"][0]["excerpt"] == chunk.content[:900]
    assert "untrusted" not in response.text
    retrieval.retrieve_for_document.return_value = (
        [result],
        FallbackReason.EMBEDDING_PROVIDERS_UNAVAILABLE,
    )
    fallback = client.post(
        f"/api/v1/documents/{document_id}/search", json={"query": "validación experimental"}
    ).json()
    assert fallback["engine"] == "text" and fallback["degraded"] and fallback["model"] is None


def test_search_requires_processed_document(client):
    register(client, "search-new@example.com")
    response = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "tesis.docx",
                valid_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    path = f"/api/v1/documents/{response.json()['id']}/search"
    assert client.post(path, json={"query": "validación"}).status_code == 409
    assert client.post(path, json={"query": " "}).status_code == 422
    assert client.post(path, json={"query": "x" * 401}).status_code == 422
