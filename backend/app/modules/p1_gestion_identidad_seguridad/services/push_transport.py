"""One provider request. Results distinguish acceptance from physical receipt."""

import json
from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class PushResult:
    state: str  # accepted, retry, permanent, gone
    code: str | None = None


def send_web(row, payload) -> PushResult:
    from pywebpush import WebPushException, webpush

    settings = get_settings()
    if not settings.push_private_key or not settings.push_public_key:
        return PushResult("retry", "not_configured")
    try:
        webpush(
            subscription_info={
                "endpoint": row.endpoint,
                "keys": {"p256dh": row.p256dh, "auth": row.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.push_private_key.get_secret_value(),
            vapid_claims={"sub": settings.push_contact},
            ttl=3600,
            timeout=5,
        )
        return PushResult("accepted")
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            return PushResult("gone", "registration_gone")
        if status is not None and 400 <= status < 500 and status not in (408, 429):
            return PushResult("permanent", "provider_rejected")
        return PushResult("retry", "provider_temporary")
    except Exception:
        return PushResult("retry", "transport_unavailable")


def send_native(row, payload) -> PushResult:
    import re

    import httpx

    from app.modules.p1_gestion_identidad_seguridad.services.native_push_service import (
        _credentials_lock,
        credentials_for,
    )

    path = get_settings().fcm_service_account_file
    if not path:
        return PushResult("retry", "not_configured")
    try:
        credentials = credentials_for(path)
        with _credentials_lock:
            if not credentials.valid:
                from google.auth.transport.requests import Request

                credentials.refresh(lambda **kwargs: Request()(**{**kwargs, "timeout": 5}))
        project = credentials.project_id
        if not re.fullmatch(r"[a-z][a-z0-9-]{4,62}", project or ""):
            return PushResult("permanent", "invalid_project")
        response = httpx.post(
            f"https://fcm.googleapis.com/v1/projects/{project}/messages:send",
            headers={"Authorization": "Bearer " + credentials.token},
            timeout=5,
            json={
                "message": {
                    "token": row.token,
                    "notification": {"title": payload["title"], "body": payload["body"]},
                    "data": {"url": payload.get("url", "/documents")},
                    "android": {
                        "ttl": "3600s",
                        "priority": "high",
                        "notification": {
                            "channel_id": "socratia_preparation",
                            "icon": "ic_notification",
                            "visibility": "PRIVATE",
                            "default_sound": True,
                            "tag": payload.get("tag", "socratia"),
                        },
                    },
                }
            },
        )
        if response.status_code == 200:
            return PushResult("accepted")
        try:
            details = response.json().get("error", {}).get("details", [])
        except (ValueError, AttributeError):
            details = []
        if any(
            isinstance(item, dict) and item.get("errorCode") == "UNREGISTERED" for item in details
        ):
            return PushResult("gone", "registration_gone")
        if 400 <= response.status_code < 500 and response.status_code not in (408, 429):
            return PushResult("permanent", "provider_rejected")
        return PushResult("retry", "provider_temporary")
    except Exception:
        return PushResult("retry", "transport_unavailable")
