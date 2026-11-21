from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.modules.p1_gestion_identidad_seguridad.models.native_push import NativePushDevice
from app.modules.p1_gestion_identidad_seguridad.models.push_delivery import PushDelivery
from app.modules.p1_gestion_identidad_seguridad.models.push_subscription import PushSubscription
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.services import push_outbox as outbox
from app.modules.p1_gestion_identidad_seguridad.services.push_transport import PushResult
from app.modules.p2_gestion_documentos_preparacion.models.preparation_task import PreparationTask
from sqlalchemy import select
from test_presentation_materials import register, upload


def event(client, db):
    register(client, "outbox-owner@example.com")
    doc = upload(client)
    task_id = client.post(
        f"/api/v1/documents/{doc}/tasks", json={"kind": "process", "request_key": str(uuid4())}
    ).json()["id"]
    task = db.get(PreparationTask, task_id)
    task.status = "SUCCEEDED"
    web = PushSubscription(
        user_id=task.user_id,
        endpoint_hash="hash",
        endpoint="https://fcm.googleapis.com/fcm/send/test",
        p256dh="fixture",
        auth="fixture",
    )
    native = NativePushDevice(
        user_id=task.user_id, token_hash="nativehash", token="fixture-native-token"
    )
    db.add_all([web, native])
    db.commit()
    return task, web, native


def test_enqueue_deduplicates_per_event_and_registration(client, db_session):
    task, web, native = event(client, db_session)
    outbox.enqueue_preparation(db_session, task)
    db_session.commit()
    outbox.enqueue_preparation(db_session, task)
    db_session.commit()
    rows = db_session.scalars(select(PushDelivery)).all()
    assert len(rows) == 2 and {row.channel for row in rows} == {"web", "native"}
    assert all(row.user_id == task.user_id and row.attempts == 0 for row in rows)


def test_retry_only_failed_device_and_preserve_event_tag(client, db_session, monkeypatch):
    task, web, native = event(client, db_session)
    outbox.enqueue_preparation(db_session, task)
    db_session.commit()
    good = Mock(return_value=PushResult("accepted"))
    flaky = Mock(side_effect=[PushResult("retry", "provider_temporary"), PushResult("accepted")])
    monkeypatch.setattr(outbox, "send_web", good)
    monkeypatch.setattr(outbox, "send_native", flaky)
    now = datetime.now(UTC) + timedelta(seconds=1)
    assert outbox.dispatch_one(db_session, now=now)
    assert outbox.dispatch_one(db_session, now=now)
    assert not outbox.dispatch_one(db_session, now=now)
    rows = db_session.scalars(select(PushDelivery)).all()
    assert {r.status for r in rows} == {"ACCEPTED", "PENDING"}
    assert outbox.dispatch_one(db_session, now=now + timedelta(seconds=61))
    assert good.call_count == 1 and flaky.call_count == 2
    assert all(r.status == "ACCEPTED" for r in rows)
    assert (
        flaky.call_args_list[0].args[1]["tag"]
        == flaky.call_args_list[1].args[1]["tag"]
        == "preparation-" + task.id
    )
    assert "document" not in flaky.call_args.args[1]["body"].lower()


def test_retry_is_bounded_and_survives_new_session(client, db_session, monkeypatch):
    task, web, native = event(client, db_session)
    db_session.delete(native)
    db_session.commit()
    outbox.enqueue_preparation(db_session, task)
    db_session.commit()
    send = Mock(return_value=PushResult("retry", "transport_unavailable"))
    monkeypatch.setattr(outbox, "send_web", send)
    now = datetime.now(UTC) + timedelta(seconds=1)
    for offset in (0, 61, 362, 1263):
        assert outbox.dispatch_one(db_session, now=now + timedelta(seconds=offset))
    row = db_session.scalar(select(PushDelivery))
    assert row.attempts == 4 and row.status == "FAILED"
    assert (
        not outbox.dispatch_one(db_session, now=now + timedelta(seconds=3600))
        and send.call_count == 4
    )
    db_session.expire_all()
    assert db_session.get(PushDelivery, row.id).status == "FAILED"


@pytest.mark.parametrize("change", ["unsubscribe", "transfer", "inactive"])
def test_each_attempt_reauthorizes_recipient(client, db_session, monkeypatch, change):
    task, web, native = event(client, db_session)
    db_session.delete(native)
    db_session.commit()
    outbox.enqueue_preparation(db_session, task)
    db_session.commit()
    if change == "unsubscribe":
        db_session.delete(web)
    elif change == "inactive":
        db_session.get(User, task.user_id).is_active = False
    else:
        register(client, "outbox-other@example.com")
        web.user_id = client.get("/api/v1/profile").json()["id"]
    db_session.commit()
    send = Mock()
    monkeypatch.setattr(outbox, "send_web", send)
    assert outbox.dispatch_one(db_session, now=datetime.now(UTC) + timedelta(seconds=1))
    assert db_session.scalar(select(PushDelivery)).status == "CANCELLED" and not send.called


def test_crashed_lease_recovers_but_no_unbounded_attempts(client, db_session, monkeypatch):
    task, web, native = event(client, db_session)
    db_session.delete(native)
    db_session.commit()
    outbox.enqueue_preparation(db_session, task)
    db_session.commit()
    row = db_session.scalar(select(PushDelivery))
    row.status = "PROCESSING"
    row.attempts = 1
    row.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()
    monkeypatch.setattr(outbox, "send_web", Mock(return_value=PushResult("accepted")))
    assert outbox.dispatch_one(db_session)
    assert row.status == "ACCEPTED" and row.attempts == 2


def test_permanent_failure_does_not_retry_and_gone_registration_is_removed(
    client, db_session, monkeypatch
):
    task, web, native = event(client, db_session)
    outbox.enqueue_preparation(db_session, task)
    db_session.commit()
    monkeypatch.setattr(
        outbox, "send_web", Mock(return_value=PushResult("permanent", "provider_rejected"))
    )
    monkeypatch.setattr(
        outbox, "send_native", Mock(return_value=PushResult("gone", "registration_gone"))
    )
    for _ in range(2):
        assert outbox.dispatch_one(db_session, now=datetime.now(UTC) + timedelta(seconds=1))
    assert not outbox.dispatch_one(db_session, now=datetime.now(UTC) + timedelta(minutes=20))
    assert db_session.get(NativePushDevice, native.id) is None
    assert all(r.status == "FAILED" for r in db_session.scalars(select(PushDelivery)).all())


def test_enqueue_failure_does_not_revert_business_completion(client, db_session, monkeypatch):
    from app.cli import preparation_worker as worker

    register(client, "outbox-commit@example.com")
    doc = upload(client)
    task_id = client.post(
        f"/api/v1/documents/{doc}/tasks", json={"kind": "process", "request_key": str(uuid4())}
    ).json()["id"]
    monkeypatch.setattr(
        worker, "enqueue_preparation", Mock(side_effect=RuntimeError("private provider text"))
    )
    assert worker.run_one(db_session, lambda *_: None)
    assert db_session.get(PreparationTask, task_id).status == "SUCCEEDED"


def test_concurrent_dispatchers_do_not_send_same_device_twice(client, db_session, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from sqlalchemy.orm import sessionmaker

    task, web, native = event(client, db_session)
    db_session.delete(native)
    db_session.commit()
    outbox.enqueue_preparation(db_session, task)
    db_session.commit()
    started, release = Event(), Event()

    def send(*_):
        started.set()
        assert release.wait(5)
        return PushResult("accepted")

    sender = Mock(side_effect=send)
    monkeypatch.setattr(outbox, "send_web", sender)
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)

    def dispatch():
        with factory() as db:
            return outbox.dispatch_one(db)

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(dispatch)
        try:
            assert started.wait(5)
            assert not dispatch()
        finally:
            release.set()
        assert pending.result(timeout=5)
    assert sender.call_count == 1
