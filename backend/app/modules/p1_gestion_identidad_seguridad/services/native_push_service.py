"""Manual FCM probes share the same transport as persistent preparation events."""

import logging
from functools import lru_cache
from threading import Lock

import httpx  # noqa: F401 -- shared transport module and compatibility for provider probes
from sqlalchemy import select

from app.core.config import get_settings
from app.modules.p1_gestion_identidad_seguridad.models.native_push import NativePushDevice
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.services.push_transport import send_native

logger = logging.getLogger(__name__)
_credentials_lock = Lock()


@lru_cache(maxsize=1)
def credentials_for(path):
    from google.oauth2 import service_account

    return service_account.Credentials.from_service_account_file(
        path, scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )


def deliver_native_push(db, user_id, payload):
    if not get_settings().fcm_service_account_file:
        return {"accepted": 0, "failed": 0}
    rows = db.scalars(
        select(NativePushDevice)
        .join(User, User.id == NativePushDevice.user_id)
        .where(NativePushDevice.user_id == user_id, User.is_active)
        .limit(5)
    ).all()
    accepted = failed = 0
    for row in rows:
        result = send_native(row, payload)
        if result.state == "accepted":
            accepted += 1
        else:
            failed += 1
            if result.state == "gone":
                db.delete(row)
                db.commit()
            logger.warning("Native push delivery failed; code=%s", result.code)
    return {"accepted": accepted, "failed": failed}
