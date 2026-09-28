from threading import Event
import time

import pytest

from app.load_testing import LoadTestManager


def test_load_test_rejects_unbounded_or_unknown_parameters() -> None:
    manager = LoadTestManager()

    with pytest.raises(ValueError, match="target_not_allowed"):
        manager.start("https://example.com", 5, 1)
    with pytest.raises(ValueError, match="duration_out_of_range"):
        manager.start("health", 61, 1)
    with pytest.raises(ValueError, match="workers_out_of_range"):
        manager.start("health", 5, 17)


def test_load_test_runs_and_reports_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.load_testing._request_once", lambda _path: (4.0, 200, None))
    manager = LoadTestManager()

    manager.start("health", 1, 2)
    deadline = time.monotonic() + 3
    result = manager.snapshot()
    while result and result["status"] == "running" and time.monotonic() < deadline:
        time.sleep(0.02)
        result = manager.snapshot()

    assert result is not None
    assert result["status"] == "completed"
    assert result["total_requests"] > 0
    assert result["failed_requests"] == 0
    assert result["latency_ms"]["p95"] == 4.0


def test_load_test_is_single_task_and_can_be_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    request_started = Event()
    release_request = Event()

    def blocked_request(_path: str) -> tuple[float, int, None]:
        request_started.set()
        release_request.wait(timeout=2)
        return 1.0, 200, None

    monkeypatch.setattr("app.load_testing._request_once", blocked_request)
    manager = LoadTestManager()
    manager.start("health", 30, 1)
    assert request_started.wait(timeout=1)

    with pytest.raises(RuntimeError, match="task_already_running"):
        manager.start("health", 5, 1)

    manager.stop()
    release_request.set()
    deadline = time.monotonic() + 2
    result = manager.snapshot()
    while result and result["status"] != "stopped" and time.monotonic() < deadline:
        time.sleep(0.02)
        result = manager.snapshot()

    assert result is not None
    assert result["status"] == "stopped"
