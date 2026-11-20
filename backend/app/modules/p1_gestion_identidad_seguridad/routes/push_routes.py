import base64
import hashlib
import time
from collections import OrderedDict
from threading import Lock
from urllib.parse import urlsplit
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import CurrentUser
from app.modules.p1_gestion_identidad_seguridad.models.push_subscription import PushSubscription
from app.modules.p1_gestion_identidad_seguridad.models.native_push import NativePushDevice

router = APIRouter()
_test_usage = OrderedDict()
_test_lock = Lock()


class NativePushInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=20, max_length=4096, pattern=r"^[A-Za-z0-9_:\-]+$")


@router.get("/native")
def native_config(user: CurrentUser):
    return {"enabled": bool(get_settings().fcm_service_account_file)}


@router.post("/native", status_code=204)
def subscribe_native(body: NativePushInput, user: CurrentUser, db: Session = Depends(get_db)):
    if not get_settings().fcm_service_account_file:
        raise HTTPException(503, "Los avisos de la APK todavía no están configurados")
    digest = hashlib.sha256(body.token.encode()).hexdigest()
    row = db.scalar(select(NativePushDevice).where(NativePushDevice.token_hash == digest))
    if row is None or row.user_id != user.id:
        count = len(db.scalars(select(NativePushDevice.id).where(NativePushDevice.user_id == user.id)).all())
        if count >= 5:
            raise HTTPException(409, "Desactiva un dispositivo antes de añadir otro")
    if row is None:
        row = NativePushDevice(token_hash=digest, token=body.token)
        db.add(row)
    row.user_id = user.id
    db.commit()
    return Response(status_code=204)


@router.delete("/native", status_code=204)
def unsubscribe_native(body: NativePushInput, user: CurrentUser, db: Session = Depends(get_db)):
    db.execute(delete(NativePushDevice).where(NativePushDevice.user_id == user.id,
        NativePushDevice.token_hash == hashlib.sha256(body.token.encode()).hexdigest()))
    db.commit()
    return Response(status_code=204)


@router.post("/native/test")
def test_native_notification(user: CurrentUser, db: Session = Depends(get_db)):
    if not get_settings().fcm_service_account_file:
        raise HTTPException(503, "Los avisos de la APK todavía no están configurados")
    with _test_lock:
        now = time.monotonic()
        key = "native:" + user.id
        if now - _test_usage.get(key, -60) < 60:
            raise HTTPException(429, "Espera un minuto antes de enviar otro aviso")
        _test_usage[key] = now
        _test_usage.move_to_end(key)
        while len(_test_usage) > 1024:
            _test_usage.popitem(last=False)
    from app.modules.p1_gestion_identidad_seguridad.services.native_push_service import deliver_native_push
    return deliver_native_push(db, user.id, {"title": "Socratia · aviso de prueba",
        "body": "Tus avisos de preparación están activos.", "url": "/documents", "tag": "socratia-native-test"})


@router.post("/test")
def test_notification(user: CurrentUser, db: Session = Depends(get_db)):
    """An explicit, bounded probe; provider acceptance is not device receipt."""
    s = get_settings()
    if not (s.push_public_key and s.push_private_key):
        raise HTTPException(503, "Los avisos no están configurados")
    with _test_lock:
        now = time.monotonic()
        if now - _test_usage.get(user.id, -60) < 60:
            raise HTTPException(429, "Espera un minuto antes de enviar otro aviso")
        _test_usage[user.id] = now
        _test_usage.move_to_end(user.id)
        while len(_test_usage) > 1024:
            _test_usage.popitem(last=False)
    from app.modules.p1_gestion_identidad_seguridad.services.push_service import deliver_push
    result = deliver_push(db, user.id, {
        "title": "Socratia · aviso de prueba",
        "body": "Los avisos están activos. Puedes volver a tu preparación.",
        "url": "/documents", "tag": "socratia-push-test",
    })
    return result


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
