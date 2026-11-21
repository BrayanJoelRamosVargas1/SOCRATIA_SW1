"""Bounded at-least-once delivery. Stable provider tags collapse repeat displays.

A provider may accept just before a crash. Exact-once receipt cannot be promised.
Registrations are re-authorized on every attempt, never copied into this queue.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.modules.p1_gestion_identidad_seguridad.models.native_push import NativePushDevice
from app.modules.p1_gestion_identidad_seguridad.models.push_delivery import PushDelivery
from app.modules.p1_gestion_identidad_seguridad.models.push_subscription import PushSubscription
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.services.push_transport import send_native, send_web
from app.modules.p2_gestion_documentos_preparacion.models.preparation_task import PreparationTask

MAX_ATTEMPTS = 4
BACKOFF_SECONDS = (60, 300, 900)
LEASE_SECONDS = 120


def enqueue_preparation(db, task):
    if task.status not in ("SUCCEEDED", "FAILED"):
        return
    existing = set(
        db.execute(
            select(PushDelivery.channel, PushDelivery.registration_id).where(
                PushDelivery.task_id == task.id
            )
        ).all()
    )
    for channel, model in (("web", PushSubscription), ("native", NativePushDevice)):
        registrations = db.scalars(
            select(model).where(model.user_id == task.user_id).limit(5)
        ).all()
        for row in registrations:
            if (channel, row.id) not in existing:
                db.add(
                    PushDelivery(
                        task_id=task.id,
                        user_id=task.user_id,
                        channel=channel,
                        registration_id=row.id,
                    )
                )
    db.flush()


def dispatch_one(db, *, now=None):
    now = now or datetime.now(UTC)
    # PROCESSING entries have a lease: a crash consumes an attempt and can be
    # retried later, rather than leaving an unbounded stuck delivery.
    delivery = db.scalar(
        select(PushDelivery)
        .where(
            PushDelivery.status.in_(("PENDING", "PROCESSING")), PushDelivery.next_attempt_at <= now
        )
        .order_by(PushDelivery.next_attempt_at, PushDelivery.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if delivery is None:
        db.rollback()
        return False
    task = db.get(PreparationTask, delivery.task_id)
    user = db.get(User, delivery.user_id)
    model = PushSubscription if delivery.channel == "web" else NativePushDevice
    registration = db.get(model, delivery.registration_id)
    created = delivery.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    if (
        not task
        or task.user_id != delivery.user_id
        or not user
        or not user.is_active
        or not registration
        or registration.user_id != delivery.user_id
    ):
        delivery.status, delivery.error_code = "CANCELLED", "recipient_unavailable"
        db.commit()
        return True
    if task.status not in ("SUCCEEDED", "FAILED"):
        delivery.status, delivery.error_code = "CANCELLED", "event_unavailable"
        db.commit()
        return True
    if delivery.attempts >= MAX_ATTEMPTS or now - created > timedelta(hours=1):
        delivery.status, delivery.error_code = "FAILED", "attempts_or_age_exceeded"
        db.commit()
        return True
    delivery.attempts += 1
    delivery.status = "PROCESSING"
    delivery.next_attempt_at = now + timedelta(seconds=LEASE_SECONDS)
    # Keep the row lock throughout the bounded send. A concurrent dispatcher
    # skips it; a crash before commit leaves it pending for a later attempt.
    # attempts are committed first so crashing senders cannot retry forever.
    delivery_id, attempts = delivery.id, delivery.attempts
    db.commit()
    delivery = db.scalar(
        select(PushDelivery).where(PushDelivery.id == delivery_id).with_for_update()
    )
    if delivery is None or delivery.status != "PROCESSING" or delivery.attempts != attempts:
        db.rollback()
        return True
    # Re-check mutable registrations after committing the lease.
    registration = db.scalar(
        select(model)
        .where(model.id == delivery.registration_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    db.refresh(user)
    if registration is None or registration.user_id != delivery.user_id or not user.is_active:
        delivery.status, delivery.error_code = "CANCELLED", "recipient_unavailable"
        db.commit()
        return True
    payload = {
        "title": "Socratia",
        "body": "Tu preparación está lista."
        if task.status == "SUCCEEDED"
        else "Una tarea requiere tu atención. Abre Socratia para revisarla.",
        "url": "/documents/" + task.document_id,
        "tag": "preparation-" + task.id,
    }
    try:
        result = (send_web if delivery.channel == "web" else send_native)(registration, payload)
        delivery.error_code = result.code
        if result.state == "accepted":
            delivery.status, delivery.accepted_at = "ACCEPTED", now
        elif result.state in ("gone", "permanent"):
            delivery.status = "FAILED"
            if result.state == "gone":
                db.delete(registration)
        elif delivery.attempts >= MAX_ATTEMPTS:
            delivery.status = "FAILED"
        else:
            delivery.status = "PENDING"
            delivery.next_attempt_at = now + timedelta(
                seconds=BACKOFF_SECONDS[delivery.attempts - 1]
            )
        db.commit()
    except Exception:
        # The persisted lease bounds recovery even if the database or sender
        # fails unexpectedly. No private error text is persisted.
        db.rollback()
    return True
