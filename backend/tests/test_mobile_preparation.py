import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from pypdf import PdfReader
from app.modules.p1_gestion_identidad_seguridad.routes.push_routes import (
    PushInput,
    validate_subscription,
)
from app.modules.p2_gestion_documentos_preparacion.services.question_export import export_questions
from test_question_banks import processed_document, register


def subscription(endpoint="https://fcm.googleapis.com/fcm/send/test"):
    enc = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")
    return PushInput(endpoint=endpoint, p256dh=enc(b"\x04" + b"a" * 64), auth=enc(b"a" * 16))


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://fcm.googleapis.com/x",
        "https://fcm.googleapis.com.evil.org/x",
        "https://127.0.0.1/private",
        "https://user:pass@fcm.googleapis.com/x",
    ],
)
def test_push_rejects_untrusted_destinations(endpoint):
    with pytest.raises(HTTPException):
        validate_subscription(subscription(endpoint))


def test_push_supports_browser_keys():
    validate_subscription(subscription())


def test_direct_pgvector_results_are_not_discarded_as_lexical_fallback(monkeypatch):
    from app.integrations.retrieval.router import RetrievalRouter
    from app.integrations.retrieval.base import RetrievalMode, FallbackReason
    from app.integrations.vector_db.pgvector_provider import PgVectorStoreProvider
    from app.integrations.vector_db.base import VectorSearchResult
    vectors = PgVectorStoreProvider(db=None)
    vectors.query = Mock(return_value=[VectorSearchResult("chunk", "Evidencia", .9, {"text": "Evidencia"}, "pgvector")])
    lexical = SimpleNamespace(search=Mock(side_effect=AssertionError("Unexpected lexical fallback")))
    embeddings = SimpleNamespace(embed_queries_for_document=Mock(return_value=[[.1]]))
    router = RetrievalRouter(embeddings, vectors, lexical)
    monkeypatch.setattr(router, "_has_any_vector_route", lambda _: True)
    profile = SimpleNamespace(id="profile", chunk_set_id="set", vector_namespace="ns", vector_index="idx", dimension=1)
    doc = SimpleNamespace(id="doc", user_id="owner", embedding_profiles=[profile], active_embedding_profile_id="profile")
    matches, reason = router.retrieve_for_document(doc, "owner", "evidencia", 3)
    assert reason == FallbackReason.NONE
    assert matches[0].retrieval_mode == RetrievalMode.VECTOR_PRIMARY
    assert matches[0].content == "Evidencia"
    lexical.search.assert_not_called()


def test_push_probe_is_authenticated_owner_scoped_and_bounded(client, monkeypatch):
    from pydantic import SecretStr
    from app.core.config import get_settings
    import pywebpush
    assert client.post("/api/v1/push/test").status_code == 401
    monkeypatch.setattr(get_settings(), "push_public_key", "public")
    monkeypatch.setattr(get_settings(), "push_private_key", SecretStr("private"))
    register(client, "probeowner@example.com")
    assert client.post("/api/v1/push/subscriptions", json=subscription().model_dump()).status_code == 204
    register(client, "probeoutsider@example.com")
    calls = []
    monkeypatch.setattr(pywebpush, "webpush", lambda **kw: calls.append(kw))
    assert client.post("/api/v1/push/test").json() == {"accepted": 0, "failed": 0}
    assert not calls
    # Log back in as the owner; only their endpoint receives the generic probe.
    assert client.post("/api/v1/auth/login", json={"email": "probeowner@example.com", "password": "secure-question-bank-password"}).status_code == 200
    assert client.post("/api/v1/push/test").json() == {"accepted": 1, "failed": 0}
    assert len(calls) == 1
    assert client.post("/api/v1/push/test").status_code == 429
    assert len(calls) == 1


def test_questions_pdf_preserves_spanish_and_excludes_answers():
    question = SimpleNamespace(
        category="METHODOLOGICAL",
        question="¿Cómo validó la metodología y sus limitaciones?",
        expected_answer_points=["SECRETO INTERNO"],
    )
    raw = export_questions(
        SimpleNamespace(questions=[question] * 24), "Tesis & resultados <ficticios>"
    )
    pdf = PdfReader(BytesIO(raw))
    text = "".join(page.extract_text() for page in pdf.pages)
    assert len(pdf.pages) > 1 and "metodología" in text and "Pregunta 24" in text
    assert "SECRETO INTERNO" not in text


def test_pdf_route_is_owner_scoped(client):
    doc = processed_document(client, "pdfowner@example.com")
    assert client.post(f"/api/v1/documents/{doc}/questions/generate").status_code == 200
    response = client.get(f"/api/v1/documents/{doc}/questions/export")
    assert response.status_code == 200 and response.content.startswith(b"%PDF")
    assert response.headers["cache-control"] == "private, no-store"
    register(client, "pdfoutsider@example.com")
    assert client.get(f"/api/v1/documents/{doc}/questions/export").status_code == 404


def test_push_and_help_require_authentication(client):
    assert client.get("/api/v1/push/config").status_code == 401
    assert (
        client.post("/api/v1/help/ask", json={"question": "Generar preguntas"}).status_code == 401
    )


def test_help_is_spanish_and_no_automatic_provider_call(client, monkeypatch):
    register(client, "guide@example.com")
    result = client.post("/api/v1/help/ask", json={"question": "Cómo descargar preguntas"}).json()
    assert result["engine"] == "guia_local" and "PDF" in result["answer"]


def test_document_limit_is_published_from_server(client):
    register(client, "limits@example.com")
    from app.core.config import get_settings

    assert (
        client.get("/api/v1/documents/capabilities").json()["max_document_size_mb"]
        == get_settings().max_document_size_mb
    )


def test_self_hosted_failure_keeps_provider_contract(monkeypatch):
    from app.integrations.llm import self_hosted
    from app.integrations.llm.base import QuestionGenerationProviderError

    monkeypatch.setattr(
        self_hosted, "completion", Mock(side_effect=RuntimeError("PRIVATE ENDPOINT"))
    )
    with pytest.raises(QuestionGenerationProviderError) as exc:
        self_hosted.SelfHostedQuestions().generate(SimpleNamespace())
    assert "PRIVATE" not in str(exc.value) and exc.value.retryable


def test_upload_more_than_twenty_mb_uses_configured_limit(client, monkeypatch):
    from app.core.config import get_settings
    from test_documents import valid_pdf

    register(client, "large@example.com")
    monkeypatch.setattr(get_settings(), "max_document_size_mb", 50)
    # A valid PDF with a large metadata comment, not decompressed images or CPU inference.
    raw = valid_pdf() + b"\n%" + b"x" * (21 * 1024 * 1024) + b"\n"
    response = client.post(
        "/api/v1/documents", files={"file": ("grande.pdf", raw, "application/pdf")}
    )
    assert response.status_code == 201
    assert response.json()["file_size"] > 20 * 1024 * 1024


def test_push_is_owner_scoped_and_failure_does_not_expose_documents(
    client, db_session, monkeypatch
):
    from app.core.config import get_settings
    from app.cli.preparation_worker import run_one
    from test_presentation_materials import upload
    from uuid import uuid4
    from pydantic import SecretStr
    import pywebpush

    register(client, "pushowner@example.com")
    monkeypatch.setattr(get_settings(), "push_public_key", "testpublic")
    monkeypatch.setattr(get_settings(), "push_private_key", SecretStr("testprivate"))
    body = subscription().model_dump()
    assert client.post("/api/v1/push/subscriptions", json=body).status_code == 204
    doc = upload(client)
    calls = []
    monkeypatch.setattr(pywebpush, "webpush", lambda **kw: calls.append(kw))
    assert (
        client.post(
            f"/api/v1/documents/{doc}/tasks", json={"kind": "process", "request_key": str(uuid4())}
        ).status_code
        == 202
    )
    run_one(db_session, lambda *_: None)
    assert len(calls) == 1 and calls[0]["timeout"] == 5
    import json
    assert "Tu preparación está lista" in json.loads(calls[0]["data"])["body"]
    assert "PRIVATE" not in calls[0]["data"]
    assert client.request("DELETE", "/api/v1/push/subscriptions", json=body).status_code == 204


def test_preparation_provider_is_selected_without_loading_models(monkeypatch):
    from app.core.config import get_settings
    from app.integrations.llm.dependencies import get_question_generation_router,get_presentation_generation_router
    settings=get_settings()
    for selected,expected in [("groq","groq"),("self_hosted","self_hosted"),("gemini","gemini")]:
        monkeypatch.setattr(settings,"preparation_primary_provider",selected)
        get_question_generation_router.cache_clear();get_presentation_generation_router.cache_clear()
        assert get_question_generation_router().primary.name==expected
        assert get_presentation_generation_router().primary.name==expected
    get_question_generation_router.cache_clear();get_presentation_generation_router.cache_clear()
