from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import httpx
import pytest

from app.integrations.embeddings.base import EmbeddingError
from app.integrations.embeddings.gemini import GeminiEmbeddingProvider
from app.integrations.retrieval.base import FallbackReason
from app.integrations.retrieval.router import RetrievalRouter
from app.integrations.vector_db.base import VectorStoreError


def setup_router(monkeypatch):
    profile = SimpleNamespace(id="profile", chunk_set_id="chunks", vector_namespace="ns",
                              vector_index="index", dimension=1)
    document = SimpleNamespace(id="document", user_id="owner", embedding_profiles=[profile],
                               active_embedding_profile_id="profile")
    embeddings = SimpleNamespace(embed_queries_for_document=Mock(return_value=[[.1], [.2], [.3]]))
    vectors = SimpleNamespace(query=Mock(return_value=[]))
    lexical = SimpleNamespace(search=Mock(return_value=[]))
    router = RetrievalRouter(embeddings, vectors, lexical)
    monkeypatch.setattr(router, "_has_any_vector_route", Mock(return_value=True))
    return router, document, embeddings, vectors, lexical


def test_all_intents_use_one_embedding_call_and_keep_owner_filters(monkeypatch):
    router, document, embeddings, vectors, lexical = setup_router(monkeypatch)
    queries = ["problema", "método", "resultados"]
    assert len(router.retrieve_many_for_document(document, "owner", queries, 3)) == 3
    embeddings.embed_queries_for_document.assert_called_once_with(document, queries)
    router._has_any_vector_route.assert_called_once_with("profile")
    assert [call.kwargs["vector"] for call in vectors.query.call_args_list] == [[.1], [.2], [.3]]
    for call in vectors.query.call_args_list:
        assert call.kwargs["filters"] == {"$and": [
            {"user_id": {"$eq": "owner"}}, {"document_id": {"$eq": "document"}}]}
    lexical.search.assert_not_called()


def test_cross_owner_batch_cannot_embed_or_search(monkeypatch):
    router, document, embeddings, vectors, lexical = setup_router(monkeypatch)
    assert router.retrieve_many_for_document(document, "outsider", ["a", "b"], 3) == [
        ([], FallbackReason.NONE), ([], FallbackReason.NONE)]
    embeddings.embed_queries_for_document.assert_not_called()
    vectors.query.assert_not_called()
    lexical.search.assert_not_called()


def test_no_synced_route_uses_local_search_without_embedding(monkeypatch):
    router, document, embeddings, vectors, lexical = setup_router(monkeypatch)
    router._has_any_vector_route.return_value = False
    results = router.retrieve_many_for_document(document, "owner", ["a", "b"], 3)
    assert all(reason == FallbackReason.NO_SYNCED_VECTOR_STORE for _, reason in results)
    embeddings.embed_queries_for_document.assert_not_called()
    vectors.query.assert_not_called()
    assert lexical.search.call_count == 2


@pytest.mark.parametrize("response", [[], [[.1]], [[], [.2], [.3]], EmbeddingError("quota")])
def test_failed_or_incomplete_batch_falls_back_without_repeating_api(monkeypatch, response):
    router, document, embeddings, vectors, lexical = setup_router(monkeypatch)
    if isinstance(response, Exception):
        embeddings.embed_queries_for_document.side_effect = response
    else:
        embeddings.embed_queries_for_document.return_value = response
    results = router.retrieve_many_for_document(document, "owner", ["a", "b", "c"], 3)
    assert all(reason == FallbackReason.EMBEDDING_PROVIDERS_UNAVAILABLE for _, reason in results)
    assert embeddings.embed_queries_for_document.call_count == 1
    assert lexical.search.call_count == 3
    vectors.query.assert_not_called()


def test_one_vector_failure_does_not_discard_other_intents(monkeypatch):
    router, document, _, vectors, lexical = setup_router(monkeypatch)
    vectors.query.side_effect = [[], VectorStoreError("offline"), []]
    results = router.retrieve_many_for_document(document, "owner", ["a", "b", "c"], 3)
    assert [reason for _, reason in results] == [FallbackReason.NONE,
        FallbackReason.VECTOR_RETRIEVAL_FAILED, FallbackReason.NONE]
    lexical.search.assert_called_once()
    assert lexical.search.call_args.kwargs["query_text"] == "b"


def test_validation_errors_still_fail_closed(monkeypatch):
    router, document, embeddings, _, lexical = setup_router(monkeypatch)
    embeddings.embed_queries_for_document.side_effect = ValueError("wrong embedding space")
    with pytest.raises(ValueError):
        router.retrieve_many_for_document(document, "owner", ["a"], 3)
    lexical.search.assert_not_called()


@pytest.mark.parametrize("status", [429, 503])
def test_interactive_embedding_does_not_sleep_or_retry_on_quota(monkeypatch, status):
    from app.integrations.embeddings import gemini
    monkeypatch.setattr(gemini.time, "sleep", Mock(side_effect=AssertionError("Interactive retry wait")))
    client = SimpleNamespace(post=Mock(return_value=httpx.Response(status)))
    with pytest.raises(EmbeddingError):
        GeminiEmbeddingProvider._post_with_retry(client, "https://example.com", {}, 6, 100,
                                                 "test", max_attempts=1)
    assert client.post.call_count == 1


def test_query_adapter_uses_one_attempt_with_short_timeout(monkeypatch):
    from app.integrations.embeddings import gemini
    provider = GeminiEmbeddingProvider(api_key="test", model="test", dimensions=1,
                                       batch_size=10, timeout_seconds=60)
    fake_client = MagicMock()
    monkeypatch.setattr(gemini.httpx, "Client", fake_client)
    post = Mock(return_value={"embeddings": [{"values": [.1]}, {"values": [.2]}]})
    monkeypatch.setattr(provider, "_post_with_retry", post)
    assert provider.embed_queries(["a", "b"]) == [[.1], [.2]]
    assert fake_client.call_args.kwargs["timeout"] == 10
    assert post.call_args.kwargs["max_attempts"] == 1


def test_query_budget_exhaustion_falls_back_without_sleep_or_http(monkeypatch):
    from app.integrations.embeddings import gemini
    from app.integrations.embeddings.rate_limiter import RateBudget
    provider = GeminiEmbeddingProvider(api_key="test", model="test", dimensions=1,
                                       batch_size=10, timeout_seconds=60)
    monkeypatch.setattr(provider.rate_limiter, "calculate_budget", lambda _: RateBudget(0, 0, 60000, False))
    monkeypatch.setattr(gemini.time, "sleep", Mock(side_effect=AssertionError("Interactive quota wait")))
    post = Mock(side_effect=AssertionError("Budget exhausted"))
    monkeypatch.setattr(provider, "_post_with_retry", post)
    with pytest.raises(EmbeddingError):
        provider.embed_queries(["a", "b"])
    post.assert_not_called()
