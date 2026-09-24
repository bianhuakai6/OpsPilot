from fastapi.testclient import TestClient

from app import inspection
from app.config import Settings
from app.main import app


def test_inspection_returns_structured_read_only_results() -> None:
    response = TestClient(app).post("/api/v1/inspections/run")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pass"
    assert body["inspection_id"].startswith("inspection-")
    assert {item["check_id"] for item in body["checks"]} >= {
        "process_liveness",
        "mysql_connectivity",
        "redis_connectivity",
    }
    assert all("evidence" in item and "recommendation" in item for item in body["checks"])


def test_inspection_checks_configuration_and_metrics() -> None:
    response = TestClient(app).post("/api/v1/inspections/run")

    checks = {item["check_id"]: item for item in response.json()["checks"]}
    assert checks["configuration_integrity"]["status"] == "pass"
    assert checks["metrics_registry"]["status"] == "pass"
    assert checks["disk_space"]["status"] in {"pass", "fail", "skipped"}
    assert checks["memory_available"]["status"] in {"pass", "fail", "skipped"}


def test_inspection_reports_invalid_configuration(monkeypatch) -> None:
    monkeypatch.setattr(inspection, "settings", Settings(storage="unsupported", port=70000))
    monkeypatch.setattr(inspection, "database_engine", None)
    monkeypatch.setattr(inspection, "redis_client", None)

    report = inspection.run_inspection()

    check = next(item for item in report["checks"] if item["check_id"] == "configuration_integrity")
    assert check["status"] == "fail"
    assert "OPSPILOT_STORAGE" in check["evidence"]
    assert "OPSPILOT_PORT" in check["evidence"]


def test_resource_checks_report_low_disk_space(monkeypatch) -> None:
    class Usage:
        total = 100
        used = 95
        free = 5

    monkeypatch.setattr(inspection.shutil, "disk_usage", lambda _: Usage())
    monkeypatch.setattr(inspection, "_memory_snapshot", lambda: (100, 50))

    checks = {item["check_id"]: item for item in inspection._resource_checks()}

    assert checks["disk_space"]["status"] == "fail"
    assert checks["disk_space"]["severity"] == "critical"
    assert checks["memory_available"]["status"] == "pass"
