import base64
import hashlib
from urllib.parse import urlsplit
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import CurrentUser
from app.modules.p1_gestion_identidad_seguridad.models.push_subscription import PushSubscription

router = APIRouter()


class PushInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoint: str = Field(min_length=20, max_length=2048)
    p256dh: str = Field(min_length=80, max_length=100)
    auth: str = Field(min_length=20, max_length=30)


def validate_subscription(body):
    try:
        url = urlsplit(body.endpoint)
        port = url.port
    except ValueError:
        raise HTTPException(422, "Dirección de notificaciones inválida") from None
    host = url.hostname or ""
    allowed = (
        "fcm.googleapis.com",
        "updates.push.services.mozilla.com",
        "push.services.mozilla.com",
        "web.push.apple.com",
        "notify.windows.com",
    )
    if (
        url.scheme != "https"
        or url.username
        or url.password
        or port not in (None, 443)
        or url.fragment
        or not any(host == d or host.endswith("." + d) for d in allowed)
    ):
        raise HTTPException(422, "Servicio de notificaciones no admitido")
    try:
        key = base64.urlsafe_b64decode(body.p256dh + "=" * (-len(body.p256dh) % 4))
        auth = base64.urlsafe_b64decode(body.auth + "=" * (-len(body.auth) % 4))
        if len(key) != 65 or key[0] != 4 or len(auth) != 16:
            raise ValueError()
    except Exception:
        raise HTTPException(422, "Suscripción de notificaciones inválida") from None


@router.get("/config")
def config(user: CurrentUser):
    s = get_settings()
    return {
        "enabled": bool(s.push_public_key and s.push_private_key),
        "public_key": s.push_public_key,
    }


@router.post("/subscriptions", status_code=204)
def subscribe(body: PushInput, user: CurrentUser, db: Session = Depends(get_db)):
    if not (get_settings().push_public_key and get_settings().push_private_key):
        raise HTTPException(503, "Las notificaciones todavía no están configuradas")
    validate_subscription(body)
    digest = hashlib.sha256(body.endpoint.encode()).hexdigest()
    row = db.scalar(select(PushSubscription).where(PushSubscription.endpoint_hash == digest))
    if row is None:
        if (
            len(
                db.scalars(
                    select(PushSubscription.id).where(PushSubscription.user_id == user.id)
                ).all()
            )
            >= 5
        ):
            raise HTTPException(409, "Desactiva un dispositivo antes de añadir otro")
        row = PushSubscription(endpoint_hash=digest)
        db.add(row)
    row.user_id = user.id
    row.endpoint = body.endpoint
    row.p256dh = body.p256dh
    row.auth = body.auth
    db.commit()
    return Response(status_code=204)


@router.delete("/subscriptions", status_code=204)
def unsubscribe(body: PushInput, user: CurrentUser, db: Session = Depends(get_db)):
    db.execute(
        delete(PushSubscription).where(
            PushSubscription.user_id == user.id,
            PushSubscription.endpoint_hash == hashlib.sha256(body.endpoint.encode()).hexdigest(),
        )
    )
    db.commit()
    return Response(status_code=204)
