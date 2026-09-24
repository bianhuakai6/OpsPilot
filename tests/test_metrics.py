from fastapi.testclient import TestClient

from app.main import app


def test_metrics_endpoint_exposes_http_metrics() -> None:
    client = TestClient(app)
    client.get("/healthz")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "opspilot_http_requests_total" in response.text
    assert "opspilot_http_request_duration_seconds" in response.text
