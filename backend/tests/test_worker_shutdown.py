from contextlib import nullcontext
from threading import Event

import pytest
from pydantic import ValidationError

from app.cli import preparation_worker as worker


def test_shutdown_finishes_current_task_without_claiming_another():
    stop = Event()
    calls = []

    def execute(db):
        calls.append("started")
        stop.set()
        calls.append("finished")
        return True

    worker.worker_loop(stop, lambda: nullcontext(None), execute)
    assert calls == ["started", "finished"]


def test_idle_wait_is_interruptible_and_does_not_take_another_task():
    class Stop:
        stopped = False
        waits = []

        def is_set(self):
            return self.stopped

        def wait(self, seconds):
            self.waits.append(seconds)
            self.stopped = True

    stop = Stop()
    worker.worker_loop(stop, lambda: nullcontext(None), lambda db: False, dispatcher=lambda db: False)
    assert stop.waits == [2]


def test_shutdown_signal_handler_is_restored(monkeypatch):
    handlers = {}
    restored = []

    def install(signum, handler):
        old = handlers.get(signum, "original")
        handlers[signum] = handler
        restored.append((signum, handler))
        return old

    def run(stop):
        handlers[worker.signal.SIGTERM](worker.signal.SIGTERM, None)
        assert stop.is_set()

    monkeypatch.setattr(worker.signal, "signal", install)
    monkeypatch.setattr(worker, "run_worker", run)
    worker.main()
    assert all(value == "original" for value in handlers.values())


@pytest.mark.parametrize("score", [-1, 101, float("nan"), float("inf"), -float("inf")])
def test_evaluator_rejects_invalid_provider_scores(score):
    from app.modules.p4_gestion_evaluacion_resultados.schemas.evaluation import TurnEvaluationResult

    with pytest.raises(ValidationError):
        TurnEvaluationResult(classification="PRECISE", score=score, strengths=[],
            weaknesses=[], missing_points=[], contradictions=[], evidence=[])
