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


def metrics_payload() -> bytes:
    return generate_latest()
