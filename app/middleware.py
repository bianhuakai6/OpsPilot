import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.metrics import http_request_duration_seconds, http_requests_total, mark_http_request_observed


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        http_requests_total.labels(request.method, request.url.path, str(response.status_code)).inc()
        http_request_duration_seconds.labels(request.method, request.url.path).observe(duration_ms / 1000)
        mark_http_request_observed()
        response.headers["X-Request-ID"] = request_id
        # 压测请求仍计入指标，但不逐条写日志，避免测试本身制造日志洪峰。
        if request.headers.get("X-OpsPilot-Load-Test") != "true":
            logging.getLogger("opspilot").info(
                "http_request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
        return response
