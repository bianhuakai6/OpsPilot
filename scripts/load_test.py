"""Run a small, read-only HTTP load test and save a JSON baseline report."""

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def percentile(values: list[float], percentage: float) -> float:
    """Return a nearest-rank percentile in milliseconds."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(percentage / 100 * len(ordered)))
    return round(ordered[rank - 1], 2)


def request_once(url: str) -> tuple[float, int, str | None]:
    """Issue one GET and return latency, HTTP status, and an optional error."""
    started = time.perf_counter()
    try:
        with urlopen(url, timeout=5) as response:
            response.read()
            return (time.perf_counter() - started) * 1000, response.status, None
    except HTTPError as error:
        return (time.perf_counter() - started) * 1000, error.code, str(error)
    except (TimeoutError, URLError, OSError) as error:
        return (time.perf_counter() - started) * 1000, 0, str(error)


def run_load_test(url: str, duration: int, workers: int) -> dict[str, object]:
    """Send concurrent read-only GET requests for a fixed time window."""
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    deadline = started + duration
    latencies: list[float] = []
    statuses: list[int] = []
    errors: list[str] = []

    # 固定并发数持续发送 GET；截止后等待已发请求完成，再统一汇总。
    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {executor.submit(request_once, url) for _ in range(workers)}
        while pending:
            completed, pending = wait(pending, timeout=max(0, deadline - time.perf_counter()), return_when=FIRST_COMPLETED)
            for future in completed:
                latency, status, error = future.result()
                latencies.append(latency)
                statuses.append(status)
                if error:
                    errors.append(error)
                if time.perf_counter() < deadline:
                    pending.add(executor.submit(request_once, url))

    elapsed = time.perf_counter() - started
    successes = sum(200 <= status < 400 for status in statuses)
    failures = len(statuses) - successes
    return {
        "started_at": started_at.isoformat(),
        "url": url,
        "configured_duration_seconds": duration,
        "actual_duration_seconds": round(elapsed, 2),
        "workers": workers,
        "total_requests": len(statuses),
        "successful_requests": successes,
        "failed_requests": failures,
        "error_rate_percent": round(failures / len(statuses) * 100, 2) if statuses else 0.0,
        "requests_per_second": round(len(statuses) / elapsed, 2) if elapsed else 0.0,
        "latency_ms": {
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "max": round(max(latencies), 2) if latencies else 0.0,
        },
        "error_samples": errors[:5],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small read-only OpsPilot HTTP load test.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/healthz")
    parser.add_argument("--duration", type=int, default=15, help="Test window in seconds (default: 15)")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent request workers (default: 8)")
    parser.add_argument("--output", type=Path, default=None, help="JSON report path")
    args = parser.parse_args()
    if args.duration < 1 or args.workers < 1:
        parser.error("--duration and --workers must be positive integers")
    return args


def main() -> int:
    args = parse_args()
    report = run_load_test(args.url, args.duration, args.workers)
    output = args.output or Path("reports/generated") / f"load-test-{datetime.now():%Y%m%d-%H%M%S}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Requests: {report['total_requests']} (failed: {report['failed_requests']})")
    print(f"Throughput: {report['requests_per_second']} req/s")
    print(f"Latency P50/P95: {report['latency_ms']['p50']}/{report['latency_ms']['p95']} ms")
    print(f"Report: {output}")
    return 0 if report["failed_requests"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
