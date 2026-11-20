import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pypdf import PdfReader
from test_question_banks import processed_document, register

from app.modules.p1_gestion_identidad_seguridad.routes.push_routes import (
    PushInput,
    validate_subscription,
)
from app.modules.p2_gestion_documentos_preparacion.services.question_export import export_questions


def subscription(endpoint="https://fcm.googleapis.com/fcm/send/test"):
    def enc(b):
        return base64.urlsafe_b64encode(b).decode().rstrip("=")
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


def test_native_push_requires_auth_and_configuration(client, monkeypatch):
    from app.core.config import get_settings
    assert client.get('/api/v1/push/native').status_code == 401
    register(client, 'native-disabled@example.com')
    monkeypatch.setattr(get_settings(), 'fcm_service_account_file', '')
    assert client.get('/api/v1/push/native').json() == {'enabled': False}
    assert client.post('/api/v1/push/native', json={'token': 'a' * 140}).status_code == 503


def test_native_status_is_read_only_and_owner_scoped(client, monkeypatch, db_session):
    from sqlalchemy import select

    from app.core.config import get_settings
    from app.modules.p1_gestion_identidad_seguridad.models.native_push import NativePushDevice
    body = {'token': 'device-token:' + 'a' * 140}
    assert client.post('/api/v1/push/native/status', json=body).status_code == 401
    monkeypatch.setattr(get_settings(), 'fcm_service_account_file', 'fixture.json')
    register(client, 'native-status-owner@example.com')
    assert client.post('/api/v1/push/native/status', json=body).json() == {'registered': False}
    assert not db_session.scalars(select(NativePushDevice)).all()
    assert client.post('/api/v1/push/native', json=body).status_code == 204
    assert client.post('/api/v1/push/native/status', json=body).json() == {'registered': True}
    register(client, 'native-status-outsider@example.com')
    assert client.post('/api/v1/push/native/status', json=body).json() == {'registered': False}
    assert len(db_session.scalars(select(NativePushDevice)).all()) == 1


def test_native_push_is_owner_scoped_and_cleans_only_unregistered_tokens(client, db_session, monkeypatch):
    import httpx
    from sqlalchemy import select

    from app.core.config import get_settings
    from app.modules.p1_gestion_identidad_seguridad.models.native_push import NativePushDevice
    from app.modules.p1_gestion_identidad_seguridad.services import native_push_service as service
    monkeypatch.setattr(get_settings(), 'fcm_service_account_file', 'test-only.json')
    register(client, 'native-owner@example.com')
    user_id = client.get('/api/v1/profile').json()['id']
    owner = {'token': 'owner-token:' + 'a' * 140}
    assert client.post('/api/v1/push/native', json=owner).status_code == 204
    assert client.post('/api/v1/push/native', json=owner).status_code == 204
    assert client.post('/api/v1/push/native', json={'token': 'https://evil.example/path'}).status_code == 422
    register(client, 'native-other@example.com')
    assert client.request('DELETE', '/api/v1/push/native', json=owner).status_code == 204
    assert client.post('/api/v1/push/native', json={'token': 'other:' + 'b' * 140}).status_code == 204
    credentials = SimpleNamespace(valid=True, project_id='socratia-fixture', token='fixture-only')
    monkeypatch.setattr(service, 'credentials_for', lambda _: credentials)
    post = Mock(return_value=httpx.Response(404, json={'error': {'details': [{'errorCode': 'UNREGISTERED'}]}}))
    monkeypatch.setattr(service.httpx, 'post', post)
    result = service.deliver_native_push(db_session, user_id, {'title':'Socratia','body':'Material listo','url':'/documents'})
    assert result == {'accepted': 0, 'failed': 1}
    assert post.call_args.kwargs['timeout'] == 5
    assert post.call_args.kwargs['json']['message']['token'] == owner['token']
    notification = post.call_args.kwargs['json']['message']['android']['notification']
    assert notification['channel_id'] == 'socratia_preparation'
    assert notification['visibility'] == 'PRIVATE'
    assert notification['default_sound'] is True
    rows = db_session.scalars(select(NativePushDevice)).all()
    assert len(rows) == 1 and rows[0].token.startswith('other:')


def test_native_push_test_is_bounded(client, monkeypatch):
    from app.core.config import get_settings
    from app.modules.p1_gestion_identidad_seguridad.services import native_push_service as service
    register(client, 'native-test@example.com')
    monkeypatch.setattr(get_settings(), 'fcm_service_account_file', 'fixture.json')
    deliver = Mock(return_value={'accepted': 1, 'failed': 0})
    monkeypatch.setattr(service, 'deliver_native_push', deliver)
    assert client.post('/api/v1/push/native/test').json()['accepted'] == 1
    assert client.post('/api/v1/push/native/test').status_code == 429
    assert deliver.call_count == 1


def test_excess_rubric_items_do_not_discard_bank_or_relax_source_checks():
    import json

    from conftest import FakeQuestionGenerationProvider

    from app.integrations.llm.base import (
        DocumentContextChunk,
        QuestionGenerationRequest,
        parse_question_bank,
        validate_question_bank,
    )
    request = QuestionGenerationRequest("Prueba", (DocumentContextChunk("owned", "Evidencia del documento", .9),))
    bank = FakeQuestionGenerationProvider(name="test", model="test").generate(request)
    data = bank.model_dump(mode="json")
    data["questions"][2]["expected_answer_points"] = ["Evidencia del documento"] * 8
    extra = dict(data["questions"][-1], question="¿Qué otra limitación de la evidencia debe explicarse ante el tribunal?")
    data["questions"].append(extra)
    result = validate_question_bank(parse_question_bank(json.dumps(data)), request)
    assert len(result.questions) == 12 and len(result.questions[2].expected_answer_points) == 6
    data["questions"][2]["source_chunk_ids"] = ["foreign-document"]
    with pytest.raises(ValueError):
        validate_question_bank(parse_question_bank(json.dumps(data)), request)


def test_groq_failed_generation_still_requires_full_local_validation(monkeypatch):
    import httpx
    from conftest import FakeQuestionGenerationProvider

    from app.integrations.llm.base import (
        DocumentContextChunk,
        QuestionGenerationProviderError,
        QuestionGenerationRequest,
    )
    from app.integrations.llm.groq import GroqQuestionGenerationProvider
    request = QuestionGenerationRequest("Prueba", (DocumentContextChunk("owned", "Evidencia del documento", .9),))
    bank = FakeQuestionGenerationProvider(name="test", model="test").generate(request)
    body = {"error": {"code": "json_validate_failed", "failed_generation": bank.model_dump_json()}}
    monkeypatch.setattr(httpx, "post", Mock(return_value=httpx.Response(400, json=body)))
    provider = GroqQuestionGenerationProvider(api_key="fixture", model="fixture", timeout_seconds=1, max_attempts=1, max_output_tokens=4096, max_context_chars=5000)
    assert len(provider.generate(request).questions) == 12
    body["error"]["failed_generation"] = bank.model_dump_json().replace('"owned"', '"foreign"')
    monkeypatch.setattr(httpx, "post", Mock(return_value=httpx.Response(400, json=body)))
    with pytest.raises(QuestionGenerationProviderError):
        provider.generate(request)


@pytest.mark.parametrize("model,expected", [("openai/gpt-oss-20b", "low"), ("other-model", None)])
def test_reasoning_budget_is_only_set_on_supported_models(monkeypatch, model, expected):
    import httpx

    from app.integrations.llm.base import DocumentContextChunk, QuestionGenerationRequest
    from app.integrations.llm.groq import GroqQuestionGenerationProvider
    post = Mock(return_value=httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]}))
    monkeypatch.setattr(httpx, "post", post)
    provider = GroqQuestionGenerationProvider(api_key="fixture", model=model, timeout_seconds=1, max_attempts=1, max_output_tokens=4096, max_context_chars=5000)
    provider._request(QuestionGenerationRequest("Prueba", (DocumentContextChunk("owned", "Evidencia", .9),)))
    assert post.call_args.kwargs["json"].get("reasoning_effort") == expected


def test_known_invalid_output_gets_one_correction_with_full_validation():
    from app.integrations.llm.base import correct_invalid_output_once
    call = Mock(side_effect=["bad", "valid"])
    def validate(raw):
        if raw != "valid":
            raise ValueError("invalid schema or source")
        return raw
    assert correct_invalid_output_once(call, validate) == "valid"
    assert call.call_count == 2
    call = Mock(return_value="bad")
    with pytest.raises(ValueError):
        correct_invalid_output_once(call, validate)
    assert call.call_count == 2


@pytest.mark.parametrize("kind", ["transient", "auth", "permanent"])
def test_correction_never_replays_network_or_auth_failures(kind):
    from app.integrations.llm.base import (
        LLMErrorKind,
        QuestionGenerationProviderError,
        correct_invalid_output_once,
    )
    call = Mock(side_effect=QuestionGenerationProviderError("unavailable", provider="test", kind=LLMErrorKind(kind)))
    with pytest.raises(QuestionGenerationProviderError):
        correct_invalid_output_once(call, lambda raw: raw)
    assert call.call_count == 1


def test_direct_pgvector_results_are_not_discarded_as_lexical_fallback(monkeypatch):
    from app.integrations.retrieval.base import FallbackReason, RetrievalMode
    from app.integrations.retrieval.router import RetrievalRouter
    from app.integrations.vector_db.base import VectorSearchResult
    from app.integrations.vector_db.pgvector_provider import PgVectorStoreProvider
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
    import pywebpush
    from pydantic import SecretStr

    from app.core.config import get_settings
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
    assert doc in client.get("/api/v1/documents/readiness").json()["ready_document_ids"]
    response = client.get(f"/api/v1/documents/{doc}/questions/export")
    assert response.status_code == 200 and response.content.startswith(b"%PDF")
    assert response.headers["cache-control"] == "private, no-store"
    register(client, "pdfoutsider@example.com")
    assert doc not in client.get("/api/v1/documents/readiness").json()["ready_document_ids"]
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
    from test_documents import valid_pdf

    from app.core.config import get_settings

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
    from uuid import uuid4

    import pywebpush
    from pydantic import SecretStr
    from test_presentation_materials import upload

    from app.cli.preparation_worker import run_one
    from app.core.config import get_settings

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
    from app.integrations.llm.dependencies import (
        get_presentation_generation_router,
        get_question_generation_router,
    )
    settings=get_settings()
    for selected,expected in [("groq","groq"),("self_hosted","self_hosted"),("gemini","gemini")]:
        monkeypatch.setattr(settings,"preparation_primary_provider",selected)
        get_question_generation_router.cache_clear()
        get_presentation_generation_router.cache_clear()
        assert get_question_generation_router().primary.name==expected
        assert get_presentation_generation_router().primary.name==expected
    get_question_generation_router.cache_clear()
    get_presentation_generation_router.cache_clear()
