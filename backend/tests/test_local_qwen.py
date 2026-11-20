import json
from unittest.mock import patch

import httpx
import pytest

from app.integrations.embeddings.base import EmbeddingDocument, EmbeddingError
from app.integrations.embeddings.local_qwen import QUERY_INSTRUCTION, LocalQwenEmbeddingProvider


@pytest.fixture
def provider(tmp_path):
    key = tmp_path / "key"
    key.write_text("private-test-key")
    return LocalQwenEmbeddingProvider(url="http://qwen:8080/v1", key_file=str(key))


def client_factory(handler):
    client = httpx.Client
    return lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs)


def test_queries_use_instruction_and_normalize(provider):
    seen = []

    def handler(request):
        assert request.url.host == "qwen"
        assert request.headers["authorization"] == "Bearer private-test-key"
        seen.append(json.loads(request.content)["input"][0])
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [2.0] + [0.0] * 1023}]})

    with patch("app.integrations.embeddings.local_qwen.httpx.Client", client_factory(handler)):
        vectors = provider.embed_queries(["validación", "resultados"])
    assert seen == [QUERY_INSTRUCTION + "validación", QUERY_INSTRUCTION + "resultados"]
    assert len(vectors) == 2 and vectors[0][0] == 1


def test_documents_cover_end_of_long_chunks_without_query_instruction(provider):
    seen = []

    def handler(request):
        seen.extend(json.loads(request.content)["input"])
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0] + [0.0] * 1023}]})

    text = "A" * 1600 + "FINAL IMPORTANTE"
    with patch("app.integrations.embeddings.local_qwen.httpx.Client", client_factory(handler)):
        batches = list(provider.embed_documents([EmbeddingDocument(None, text)]))
    assert "".join(seen) == text
    assert max(map(len, seen)) <= 1600
    assert batches[0][0][0] == 1


@pytest.mark.parametrize("vector", [[1.0] * 768, [0.0] * 1024, [True] * 1024, ["x"] * 1024])
def test_rejects_bad_vectors_without_exposing_payload(provider, vector):
    def handler(request):
        return httpx.Response(
            200, json={"data": [{"index": 0, "embedding": vector}], "secret": "private-text"}
        )

    with patch("app.integrations.embeddings.local_qwen.httpx.Client", client_factory(handler)):
        with pytest.raises(EmbeddingError, match="^Local Qwen embedding unavailable$"):
            provider.embed_queries(["consulta"])


def test_provider_failure_does_not_call_an_external_service(provider):
    calls = []

    def handler(request):
        calls.append(request.url.host)
        return httpx.Response(503, text="private-test-key private document")

    with patch("app.integrations.embeddings.local_qwen.httpx.Client", client_factory(handler)):
        with pytest.raises(EmbeddingError) as error:
            provider.embed_queries(["consulta"])
    assert calls == ["qwen"]
    assert "private" not in str(error.value)


def test_missing_key_is_safe(tmp_path):
    provider = LocalQwenEmbeddingProvider(
        url="http://qwen:8080/v1", key_file=str(tmp_path / "missing")
    )
    with pytest.raises(EmbeddingError):
        provider.embed_queries(["consulta"])
