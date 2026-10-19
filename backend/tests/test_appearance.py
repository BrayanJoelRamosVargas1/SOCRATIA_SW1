import base64
import json
from unittest.mock import Mock

import httpx
import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.modules.p3_gestion_simulacion.services.appearance_service import AppearanceService

JPEG = base64.b64encode(b"\xff\xd8\xff" + b"test-frame").decode()


def result(**changes):
    return {
        "person_present": True, "upper_body_visible": True,
        "jacket": True, "collared_shirt": True, "tie": False,
        "presentation": "formal", "confidence": .95,
        "feedback": "Se observa saco y camisa con cuello; la corbata es opcional.",
        **changes,
    }


def provider_response(monkeypatch, payload):
    post = Mock(return_value=httpx.Response(200, json={
        "candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}],
    }, request=httpx.Request("POST", "https://example.test")))
    monkeypatch.setattr("app.modules.p3_gestion_simulacion.services.appearance_service.httpx.post", post)
    return post


def test_observed_formal_clothing_without_mandatory_tie(monkeypatch):
    post = provider_response(monkeypatch, result())
    observed = AppearanceService(Settings(gemini_api_key="test-key")).analyze(JPEG)
    assert observed.presentation == "formal"
    assert observed.jacket is True and observed.tie is False
    sent = post.call_args.kwargs["json"]
    assert sent["contents"][0]["parts"][0]["inlineData"]["mimeType"] == "image/jpeg"


@pytest.mark.parametrize("changes", [
    {"person_present": False}, {"upper_body_visible": False}, {"confidence": .4},
])
def test_insufficient_evidence_clears_clothing_claims(monkeypatch, changes):
    provider_response(monkeypatch, result(**changes))
    observed = AppearanceService(Settings(gemini_api_key="test-key")).analyze(JPEG)
    assert observed.presentation == "uncertain"
    assert observed.jacket is observed.collared_shirt is observed.tie is None


@pytest.mark.parametrize("image", ["not-base64", base64.b64encode(b"not-jpeg").decode()])
def test_invalid_input_does_not_call_provider(monkeypatch, image):
    post = provider_response(monkeypatch, result())
    with pytest.raises(HTTPException) as error:
        AppearanceService(Settings(gemini_api_key="test-key")).analyze(image)
    assert error.value.status_code == 422
    post.assert_not_called()


def test_missing_provider_is_explicit(monkeypatch):
    post = provider_response(monkeypatch, result())
    with pytest.raises(HTTPException) as error:
        AppearanceService(Settings(gemini_api_key=None)).analyze(JPEG)
    assert error.value.status_code == 503
    post.assert_not_called()


def test_provider_failure_does_not_invent_a_result(monkeypatch):
    monkeypatch.setattr("app.modules.p3_gestion_simulacion.services.appearance_service.httpx.post", Mock(side_effect=httpx.ConnectError("offline")))
    with pytest.raises(HTTPException) as error:
        AppearanceService(Settings(gemini_api_key="test-key")).analyze(JPEG)
    assert error.value.status_code == 503


def test_invalid_provider_payload_is_unavailable(monkeypatch):
    provider_response(monkeypatch, {"presentation": "formal"})
    with pytest.raises(HTTPException) as error:
        AppearanceService(Settings(gemini_api_key="test-key")).analyze(JPEG)
    assert error.value.status_code == 503


def test_visible_bare_torso_cannot_be_formal(monkeypatch):
    provider_response(monkeypatch, result(upper_body_covered=False, presentation="formal"))
    observed = AppearanceService(Settings(gemini_api_key="test-key")).analyze(JPEG)
    assert observed.presentation == "incomplete"
    assert "prenda" in observed.feedback


def test_casual_clothing_is_not_silently_approved(monkeypatch):
    provider_response(monkeypatch, result(jacket=False, collared_shirt=False, upper_body_covered=True, presentation="casual"))
    observed = AppearanceService(Settings(gemini_api_key="test-key")).analyze(JPEG)
    assert observed.presentation == "casual" and observed.jacket is False


def test_cropped_bare_shoulders_do_not_certify_shirtlessness(monkeypatch):
    provider_response(monkeypatch, result(upper_body_visible=False, upper_body_covered=False, presentation="incomplete"))
    observed = AppearanceService(Settings(gemini_api_key="test-key")).analyze(JPEG)
    assert observed.presentation == "uncertain" and observed.upper_body_covered is None


def test_local_crop_evidence_overrides_a_formal_guess(monkeypatch):
    provider_response(monkeypatch, result(upper_body_covered=True, presentation="formal"))
    observed = AppearanceService(Settings(gemini_api_key="test-key")).analyze(JPEG, torso_in_frame=False)
    assert observed.presentation == "uncertain"
    assert observed.jacket is None and observed.upper_body_covered is None


def test_timeout_has_clear_message_without_logging_image_or_secret(monkeypatch, caplog):
    monkeypatch.setattr("app.modules.p3_gestion_simulacion.services.appearance_service.httpx.post", Mock(side_effect=httpx.ReadTimeout("provider-supplied-sensitive-detail")))
    with pytest.raises(HTTPException) as error:
        AppearanceService(Settings(gemini_api_key="private-test-secret")).analyze(JPEG)
    assert error.value.status_code == 503
    assert "tardando" in error.value.detail
    assert "ReadTimeout" in caplog.text
    assert "private-test-secret" not in caplog.text
    assert "provider-supplied-sensitive-detail" not in caplog.text
    assert JPEG not in caplog.text
