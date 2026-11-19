"""Best-effort bounded Web Push; no document text or provider credentials."""

import json
import logging
from sqlalchemy import select
from app.core.config import get_settings
from app.modules.p1_gestion_identidad_seguridad.models.push_subscription import PushSubscription
from app.modules.p1_gestion_identidad_seguridad.models.user import User

logger = logging.getLogger(__name__)


def notify_preparation(db, task):
    s = get_settings()
    if not s.push_private_key or not s.push_public_key:
        return
    from pywebpush import webpush, WebPushException

    subscriptions = db.scalars(
        select(PushSubscription).join(User, User.id == PushSubscription.user_id)
        .where(PushSubscription.user_id == task.user_id, User.is_active).limit(5)
    ).all()
    # Generic text protects privacy on the lock screen.
    data = json.dumps(
        {
            "title": "Socratia",
            "body": "Tu preparación está lista."
            if task.status == "SUCCEEDED"
            else "Una tarea requiere tu atención. Abre Socratia para revisarla.",
            "url": "/documents/" + task.document_id,
            "tag": "preparation-" + task.id,
        }
    )
    for row in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": row.endpoint,
                    "keys": {"p256dh": row.p256dh, "auth": row.auth},
                },
                data=data,
                vapid_private_key=s.push_private_key.get_secret_value(),
                vapid_claims={"sub": s.push_contact},
                ttl=3600,
                timeout=5,
            )
        except WebPushException as exc:
            if exc.response is not None and exc.response.status_code in (404, 410):
                db.delete(row)
                db.commit()
            logger.warning(
                "Push delivery failed; status=%s", getattr(exc.response, "status_code", None)
            )
        except Exception:
            logger.warning("Push delivery unavailable")
