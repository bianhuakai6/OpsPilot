from fastapi.testclient import TestClient

from app import metrics
from app.main import app
from app.slo import SLOConfig, _is_business_request, evaluate_slo, slo_snapshot


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


def test_slo_does_not_claim_success_without_latency_samples() -> None:
    result = evaluate_slo(10, 0, None)

    assert result["status"] == "no_data"
    assert result["availability_percent"] == 100.0


def test_slo_rejects_inconsistent_request_counts() -> None:
    try:
        evaluate_slo(2, 3, 100)
        raise AssertionError("failed request count cannot exceed total requests")
    except ValueError as error:
        assert "失败请求数不能超过总请求数" in str(error)


def test_slo_counts_only_user_business_routes() -> None:
    assert _is_business_request("/api/v1/activities/activity-001")
    assert _is_business_request("/api/v1/activities/activity-001/reservations")
    assert not _is_business_request("/readyz")
    assert not _is_business_request("/api/v1/inspections/run")
    assert not _is_business_request("/api/v1/slo")


def test_slo_snapshot_excludes_health_probe_requests() -> None:
    before = slo_snapshot()["observed"]["total_requests"]
    metrics.http_requests_total.labels("GET", "/api/v1/activities/slo-test", "200").inc()
    metrics.http_requests_total.labels("GET", "/readyz", "503").inc()

    after = slo_snapshot()["observed"]["total_requests"]

    assert after == before + 1


def test_slo_targets_reject_impossible_or_invalid_values() -> None:
    try:
        SLOConfig(100, 500)
        raise AssertionError("100% availability leaves no measurable error budget")
    except ValueError as error:
        assert "小于 100" in str(error)

    try:
        SLOConfig(99.9, 0)
        raise AssertionError("P95 latency target must be positive")
    except ValueError as error:
        assert "必须大于 0" in str(error)


def test_slo_endpoint_returns_structured_snapshot() -> None:
    response = TestClient(app).get("/api/v1/slo")

    assert response.status_code == 200
    body = response.json()
    assert body["window"] == "process_lifetime"
    assert "targets" in body
    assert "observed" in body
