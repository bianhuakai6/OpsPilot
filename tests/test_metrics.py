from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import metrics
from app.main import app


def test_metrics_endpoint_exposes_http_metrics() -> None:
    client = TestClient(app)
    client.get("/healthz")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "opspilot_http_requests_total" in response.text
    assert "opspilot_http_request_duration_seconds" in response.text


def test_metrics_freshness_detects_stale_observation() -> None:
    metrics.last_http_request_at = datetime.now(timezone.utc) - timedelta(minutes=6)

    status, evidence = metrics.metrics_freshness()

    assert status == "fail"
    assert "超过 300 秒窗口" in evidence


def test_metrics_freshness_skips_cold_start(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "last_http_request_at", None)

    status, evidence = metrics.metrics_freshness()

    assert status == "skipped"
    assert "尚未观察到" in evidence
