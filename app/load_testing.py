from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from threading import Event, Lock, Thread
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

# 压测目标固定为只读接口，避免演示页面触发业务写入。
LOAD_TEST_TARGETS = {
    "health": ("进程健康检查", "/healthz"),
    "readiness": ("依赖就绪检查", "/readyz"),
    "activity": ("资源详情查询", "/api/v1/activities/activity-001"),
}
MAX_DURATION_SECONDS = 30
MAX_WORKERS = 8
MAX_REQUESTS = 100_000


def _percentile(values: list[float], percentage: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((percentage / 100) * len(ordered) + 0.999999) - 1))
    return round(ordered[index], 2)


def _request_once(path: str) -> tuple[float, int, str | None]:
    started = time.perf_counter()
    try:
        request = Request(
            f"http://127.0.0.1:{_server_port()}{path}",
            headers={"X-OpsPilot-Load-Test": "true"},
        )
        with urlopen(request, timeout=3) as response:
            response.read()
            return (time.perf_counter() - started) * 1000, response.status, None
    except HTTPError as error:
        return (time.perf_counter() - started) * 1000, error.code, str(error)
    except (TimeoutError, URLError, OSError) as error:
        return (time.perf_counter() - started) * 1000, 0, str(error)


def _server_port() -> int:
    from app.runtime import settings

    return settings.port


class LoadTestManager:
    """Manage one bounded local load-test task and its in-memory progress."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._task: dict[str, object] | None = None
        self._stop_event: Event | None = None

    def start(self, target: str, duration: int, workers: int) -> dict[str, object]:
        if target not in LOAD_TEST_TARGETS:
            raise ValueError("target_not_allowed")
        if not 1 <= duration <= MAX_DURATION_SECONDS:
            raise ValueError("duration_out_of_range")
        if not 1 <= workers <= MAX_WORKERS:
            raise ValueError("workers_out_of_range")

        with self._lock:
            if self._task and self._task["status"] in {"running", "stopping"}:
                raise RuntimeError("task_already_running")
            title, path = LOAD_TEST_TARGETS[target]
            self._stop_event = Event()
            self._task = {
                "task_id": str(uuid4()),
                "status": "running",
                "target": target,
                "target_name": title,
                "path": path,
                "duration_seconds": duration,
                "workers": workers,
                "completion_reason": None,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "_started_monotonic": time.monotonic(),
                "elapsed_seconds": 0.0,
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "requests_per_second": 0.0,
                "error_rate_percent": 0.0,
                "latency_ms": {"p50": 0.0, "p95": 0.0, "max": 0.0},
                "latency_samples": [],
                "error_samples": [],
            }
            task_id = str(self._task["task_id"])
            stop_event = self._stop_event
        Thread(target=self._run, args=(task_id, path, duration, workers, stop_event), daemon=True).start()
        return self.snapshot()  # type: ignore[return-value]

    def stop(self) -> dict[str, object] | None:
        with self._lock:
            if not self._task or self._task["status"] != "running":
                return self._copy_task()
            self._task["status"] = "stopping"
            if self._stop_event:
                self._stop_event.set()
            return self._copy_task()

    def snapshot(self) -> dict[str, object] | None:
        with self._lock:
            task = self._copy_task()
            if task and task["status"] in {"running", "stopping"}:
                elapsed = min(time.monotonic() - float(task.pop("_started_monotonic", time.monotonic())), float(task["duration_seconds"]))
                task["elapsed_seconds"] = round(elapsed, 2)
                # Recalculate throughput from completed requests and current elapsed time.
                task["requests_per_second"] = round(int(task["total_requests"]) / elapsed, 2) if elapsed else 0.0
            if task:
                task.pop("_started_monotonic", None)
            return task

    def _copy_task(self) -> dict[str, object] | None:
        return dict(self._task) if self._task else None

    def _run(self, task_id: str, path: str, duration: int, workers: int, stop_event: Event) -> None:
        started = time.monotonic()
        deadline = started + duration
        latencies: list[float] = []
        statuses: list[int] = []
        errors: list[str] = []
        last_progress_at = started
        try:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                pending = {executor.submit(_request_once, path) for _ in range(min(workers, MAX_REQUESTS))}
                while pending:
                    completed, pending = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
                    for future in completed:
                        latency, status, error = future.result()
                        latencies.append(latency)
                        statuses.append(status)
                        if error and len(errors) < 5:
                            errors.append(error)
                        if time.monotonic() < deadline and not stop_event.is_set() and len(statuses) + len(pending) < MAX_REQUESTS:
                            pending.add(executor.submit(_request_once, path))
                        now = time.monotonic()
                        if now - last_progress_at >= 0.5 or now >= deadline or not pending:
                            self._publish_progress(task_id, started, duration, latencies, statuses, errors)
                            last_progress_at = now

            elapsed = max(time.monotonic() - started, 0.001)
            successes = sum(200 <= status < 400 for status in statuses)
            failures = len(statuses) - successes
            with self._lock:
                if not self._task or self._task["task_id"] != task_id:
                    return
                self._task.update({
                    "status": "stopped" if stop_event.is_set() else "completed",
                    "completion_reason": (
                        "user_stopped" if stop_event.is_set()
                        else "request_limit_reached" if len(statuses) >= MAX_REQUESTS
                        else "duration_elapsed"
                    ),
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "elapsed_seconds": round(elapsed, 2),
                    "total_requests": len(statuses),
                    "successful_requests": successes,
                    "failed_requests": failures,
                    "requests_per_second": round(len(statuses) / elapsed, 2),
                    "error_rate_percent": round(failures / len(statuses) * 100, 2) if statuses else 0.0,
                    "latency_ms": {
                        "p50": _percentile(latencies, 50),
                        "p95": _percentile(latencies, 95),
                        "max": round(max(latencies), 2) if latencies else 0.0,
                    },
                    "latency_samples": [round(value, 2) for value in latencies[-120:]],
                    "error_samples": errors,
                })
        except Exception as error:
            with self._lock:
                if self._task and self._task["task_id"] == task_id:
                    self._task.update({"status": "failed", "error_samples": [str(error)]})

    def _publish_progress(
        self,
        task_id: str,
        started: float,
        duration: int,
        latencies: list[float],
        statuses: list[int],
        errors: list[str],
    ) -> None:
        elapsed = max(time.monotonic() - started, 0.001)
        successes = sum(200 <= status < 400 for status in statuses)
        failures = len(statuses) - successes
        with self._lock:
            if not self._task or self._task["task_id"] != task_id:
                return
            self._task.update({
                "elapsed_seconds": round(min(elapsed, duration), 2),
                "total_requests": len(statuses),
                "successful_requests": successes,
                "failed_requests": failures,
                "requests_per_second": round(len(statuses) / elapsed, 2),
                "error_rate_percent": round(failures / len(statuses) * 100, 2) if statuses else 0.0,
                "latency_ms": {
                    "p50": _percentile(latencies, 50),
                    "p95": _percentile(latencies, 95),
                    "max": round(max(latencies), 2) if latencies else 0.0,
                },
                "latency_samples": [round(value, 2) for value in latencies[-120:]],
                "error_samples": list(errors),
            })


load_test_manager = LoadTestManager()
