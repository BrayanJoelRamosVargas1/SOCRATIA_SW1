"""Bounded FCM HTTP v1 delivery. No custom URLs or credentials from clients."""
import logging
import re
from functools import lru_cache
from threading import Lock
import httpx
from sqlalchemy import select
from app.core.config import get_settings
from app.modules.p1_gestion_identidad_seguridad.models.native_push import NativePushDevice
from app.modules.p1_gestion_identidad_seguridad.models.user import User

logger = logging.getLogger(__name__)
_credentials_lock = Lock()


@lru_cache(maxsize=1)
def credentials_for(path):
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_file(path,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"])


def deliver_native_push(db, user_id, payload):
    path = get_settings().fcm_service_account_file
    if not path:
        return {"accepted": 0, "failed": 0}
    devices = db.scalars(select(NativePushDevice).join(User, User.id == NativePushDevice.user_id)
        .where(NativePushDevice.user_id == user_id, User.is_active).limit(5)).all()
    if not devices:
        return {"accepted": 0, "failed": 0}
    try:
        credentials = credentials_for(path)
        # A single refresh shared by worker requests. Bound connection and response time.
        with _credentials_lock:
            if not credentials.valid:
                from google.auth.transport.requests import Request
                credentials.refresh(lambda **kwargs: Request()(**{**kwargs, "timeout": 5}))
        project = credentials.project_id
        if not re.fullmatch(r"[a-z][a-z0-9-]{4,62}", project or ""):
            raise ValueError("Invalid project identifier")
    except Exception:
        logger.warning("Native push credentials unavailable")
        return {"accepted": 0, "failed": len(devices)}
    accepted = failed = 0
    for device in devices:
        try:
            response = httpx.post(f"https://fcm.googleapis.com/v1/projects/{project}/messages:send",
                headers={"Authorization": "Bearer " + credentials.token}, timeout=5,
                json={"message": {"token": device.token,
                    "notification": {"title": payload["title"], "body": payload["body"]},
                    "data": {"url": payload.get("url", "/documents")},
                    "android": {"ttl": "3600s", "priority": "normal", "notification": {"tag": payload.get("tag", "socratia")}}}})
            if response.status_code == 200:
                accepted += 1
                continue
            failed += 1
            # Only a token-specific permanent failure removes a registration.
            try:
                details = response.json().get("error", {}).get("details", [])
            except (ValueError, AttributeError):
                details = []
            if any(item.get("errorCode") == "UNREGISTERED" for item in details if isinstance(item, dict)):
                db.delete(device)
                db.commit()
            logger.warning("Native push delivery failed; status=%s", response.status_code)
        except Exception:
            failed += 1
            logger.warning("Native push delivery unavailable")
    return {"accepted": accepted, "failed": failed}
