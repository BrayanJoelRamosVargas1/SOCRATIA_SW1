from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from app.core.config import get_settings
from app.modules.p1_gestion_identidad_seguridad.services import native_push_service as native
from app.modules.p1_gestion_identidad_seguridad.services import push_transport as transport


@pytest.mark.parametrize(
    "status,error,state",
    [
        (200, None, "accepted"),
        (429, None, "retry"),
        (503, None, "retry"),
        (400, None, "permanent"),
        (404, "UNREGISTERED", "gone"),
        (404, None, "permanent"),
    ],
)
def test_native_transport_classifies_provider_results_without_storing_secrets(
    monkeypatch, status, error, state
):
    monkeypatch.setattr(get_settings(), "fcm_service_account_file", "fixture-only.json")
    monkeypatch.setattr(
        native,
        "credentials_for",
        lambda _: SimpleNamespace(valid=True, project_id="socratia-test", token="private-key"),
    )
    response = httpx.Response(status, json={"error": {"details": [{"errorCode": error}]}})
    post = Mock(return_value=response)
    monkeypatch.setattr(httpx, "post", post)
    result = transport.send_native(
        SimpleNamespace(token="private-token"),
        {
            "title": "Socratia",
            "body": "Material listo",
            "url": "/documents/test",
            "tag": "preparation-event",
        },
    )
    assert result.state == state and "private" not in str(result)
    assert post.call_count == 1 and post.call_args.kwargs["timeout"] == 5
    assert (
        post.call_args.kwargs["json"]["message"]["android"]["notification"]["tag"]
        == "preparation-event"
    )


@pytest.mark.parametrize(
    "status,state", [(429, "retry"), (503, "retry"), (400, "permanent"), (410, "gone")]
)
def test_web_transport_has_bounded_request_and_classifies_status(monkeypatch, status, state):
    import pywebpush
    from pydantic import SecretStr

    monkeypatch.setattr(get_settings(), "push_private_key", SecretStr("private-key"))
    monkeypatch.setattr(get_settings(), "push_public_key", "fixture")
    post = Mock(
        side_effect=pywebpush.WebPushException("PRIVATE DOCUMENT", response=httpx.Response(status))
    )
    monkeypatch.setattr(pywebpush, "webpush", post)
    result = transport.send_web(
        SimpleNamespace(endpoint="https://fcm.googleapis.com/test", p256dh="key", auth="auth"),
        {"body": "Material listo"},
    )
    assert result.state == state and "PRIVATE" not in str(result)
    assert post.call_args.kwargs["timeout"] == 5
