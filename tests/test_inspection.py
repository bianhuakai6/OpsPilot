from fastapi.testclient import TestClient

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
