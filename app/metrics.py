from datetime import datetime, timezone

from prometheus_client import Counter, Histogram, generate_latest


# HTTP 可观测性指标
http_requests_total = Counter(
    "opspilot_http_requests_total",
    "Total HTTP requests handled by OpsPilot.",
    ("method", "path", "status"),
)
http_request_duration_seconds = Histogram(
    "opspilot_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "path"),
)

# 记录最近一次请求完成时间，用于区分“指标存在”和“指标持续更新”。
last_http_request_at: datetime | None = None


def mark_http_request_observed() -> None:
    global last_http_request_at
    last_http_request_at = datetime.now(timezone.utc)


def metrics_freshness(now: datetime | None = None, max_age_seconds: int = 300) -> tuple[str, str]:
    """返回 freshness 状态，未有请求时不将冷启动误报为故障。"""
    if last_http_request_at is None:
        return "skipped", "尚未观察到已完成的 HTTP 请求"
    current = now or datetime.now(timezone.utc)
    age_seconds = max(0, (current - last_http_request_at).total_seconds())
    if age_seconds > max_age_seconds:
        return "fail", f"HTTP 指标距最近一次请求已 {int(age_seconds)} 秒，超过 {max_age_seconds} 秒窗口"
    return "pass", f"HTTP 指标最近 {int(age_seconds)} 秒内仍在更新"


def metrics_payload() -> bytes:
    return generate_latest()
