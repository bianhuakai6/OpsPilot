from fastapi.testclient import TestClient

from app.main import app
from app.slo import SLOConfig, evaluate_slo


def test_slo_passes_when_availability_and_p95_meet_targets() -> None:
    result = evaluate_slo(1000, 1, 240, SLOConfig(99.9, 500))

    assert result["status"] == "pass"
    assert result["availability_percent"] == 99.9
    assert result["error_budget_consumed_percent"] == 100.0


def test_slo_fails_when_error_budget_or_latency_is_exceeded() -> None:
    result = evaluate_slo(1000, 3, 600, SLOConfig(99.9, 500))

    assert result["status"] == "fail"
    assert result["error_budget_consumed_percent"] == 300.0


def test_slo_reports_no_data_without_requests() -> None:
    result = evaluate_slo(0, 0, None)

    assert result["status"] == "no_data"
    assert result["availability_percent"] is None


def test_slo_endpoint_returns_structured_snapshot() -> None:
    response = TestClient(app).get("/api/v1/slo")

    assert response.status_code == 200
    body = response.json()
    assert body["window"] == "process_lifetime"
    assert "targets" in body
    assert "observed" in body
