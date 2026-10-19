from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.modules.p4_gestion_evaluacion_resultados.services.context_selection import select_evaluation_context


def test_small_document_preserves_all_evidence():
    assert select_evaluation_context(["uno", "dos"], "tema", [], 100) == "uno\n\ndos"


def test_large_document_selects_relevant_evidence_under_hard_character_limit():
    chunks = ["Historia del proyecto. " * 100, "Método de evaluación: validación cruzada y precisión. " * 30, "Presupuesto financiero. " * 100]
    result = select_evaluation_context(chunks, "¿Cómo validaste el método?", ["validación cruzada", "precisión"], 1000)
    assert len(result) <= 1000
    assert "validación cruzada" in result
    assert "Presupuesto" not in result


def test_empty_evidence_stays_empty():
    assert select_evaluation_context([], "pregunta", None, 1000) == ""


def test_private_trial_registration_does_not_create_account(monkeypatch):
    from app.modules.p1_gestion_identidad_seguridad.routes import auth_routes
    service = Mock()
    monkeypatch.setattr(auth_routes, "get_settings", lambda: SimpleNamespace(public_registration_enabled=False))
    monkeypatch.setattr(auth_routes, "AuthService", service)
    with pytest.raises(HTTPException) as error:
        auth_routes.register(Mock(), Mock(), Mock(), Mock())
    assert error.value.status_code == 403
    service.assert_not_called()


def test_pgvector_configuration_does_not_initialize_external_store(monkeypatch):
    from app.integrations.vector_db import dependencies
    external = Mock()
    monkeypatch.setattr(dependencies, "get_settings", lambda: SimpleNamespace(vector_primary_provider="pgvector"))
    monkeypatch.setattr(dependencies, "PineconeVectorStoreProvider", external)
    assert isinstance(dependencies.get_vector_store_provider(Mock()), dependencies.PgVectorStoreProvider)
    external.assert_not_called()


def test_paid_tts_can_be_disabled_even_with_a_configured_key(monkeypatch):
    from app.integrations.tts import dependencies
    dependencies.get_tts_provider.cache_clear()
    monkeypatch.setattr(dependencies, "get_settings", lambda: SimpleNamespace(voice_tts_enabled=False,elevenlabs_api_key=SecretStr("configured-but-disabled"),elevenlabs_voice_id="voice"))
    try:
        assert dependencies.get_tts_provider().api_key is None
    finally:
        dependencies.get_tts_provider.cache_clear()


@pytest.mark.asyncio
async def test_evaluator_has_single_structured_attempt_and_output_bound():
    from app.modules.p4_gestion_evaluacion_resultados.services.evaluator import Evaluator
    evaluator = Evaluator.__new__(Evaluator)
    create = AsyncMock(return_value="evaluated")
    evaluator.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    evaluator.model = "test-model"
    evaluator.temperature = 0
    assert await evaluator.evaluate_turn("q", "a", "evidence") == "evaluated"
    assert create.call_args.kwargs["max_retries"] == 1
    assert create.call_args.kwargs["max_tokens"] == 2048
