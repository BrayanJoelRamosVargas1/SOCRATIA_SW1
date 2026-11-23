import httpx
import pytest

from app.core.config import get_settings
from app.integrations.llm import self_hosted


def test_self_hosted_uses_existing_private_key_file(monkeypatch, tmp_path):
    settings = get_settings()
    key = tmp_path / "model-key"
    key.write_text("test-file-key\n", encoding="utf-8")
    monkeypatch.setattr(settings, "self_hosted_llm_url", "http://private-chat:8080/v1")
    monkeypatch.setattr(settings, "self_hosted_llm_key", None)
    monkeypatch.setattr(settings, "self_hosted_llm_key_file", str(key))
    original = httpx.Client
    observed = []

    def handler(request):
        observed.append(request.headers["Authorization"])
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "Una hipótesis se contrasta con evidencia."},
                    }
                ]
            },
        )

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    assert self_hosted.is_configured(settings)
    answer = self_hosted.completion("Español", "Hipótesis", timeout_seconds=45)
    assert observed == ["Bearer test-file-key"] and "test-file-key" not in answer


@pytest.mark.parametrize("value", ["", "bad key", "x" * 257])
def test_invalid_private_key_file_is_rejected(monkeypatch, tmp_path, value):
    settings = get_settings()
    key = tmp_path / "model-key"
    key.write_text(value, encoding="utf-8")
    monkeypatch.setattr(settings, "self_hosted_llm_url", "http://private-chat:8080/v1")
    monkeypatch.setattr(settings, "self_hosted_llm_key", None)
    monkeypatch.setattr(settings, "self_hosted_llm_key_file", str(key))
    with pytest.raises(ValueError, match="invalid_private_model_key"):
        self_hosted._private_key(settings)
