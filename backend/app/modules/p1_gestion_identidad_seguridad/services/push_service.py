"""Manual Web Push probes; preparation events use the persistent outbox."""

import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.modules.p1_gestion_identidad_seguridad.models.push_subscription import PushSubscription
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.services.push_transport import send_web

logger = logging.getLogger(__name__)


def deliver_push(db, user_id, payload):
    settings = get_settings()
    if not settings.push_private_key or not settings.push_public_key:
        return {"accepted": 0, "failed": 0}
    rows = db.scalars(
        select(PushSubscription)
        .join(User, User.id == PushSubscription.user_id)
        .where(PushSubscription.user_id == user_id, User.is_active)
        .limit(5)
    ).all()
    accepted = failed = 0
    for row in rows:
        result = send_web(row, payload)
        if result.state == "accepted":
            accepted += 1
        else:
            failed += 1
            if result.state == "gone":
                db.delete(row)
                db.commit()
            logger.warning("Push delivery failed; code=%s", result.code)
    return {"accepted": accepted, "failed": failed}
