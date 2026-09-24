from fastapi.testclient import TestClient

from app.main import app


def test_inspection_history_contains_completed_report() -> None:
    client = TestClient(app)
    created = client.post("/api/v1/inspections/run").json()

    response = client.get("/api/v1/inspections/history")

    assert response.status_code == 200
    assert response.json()["items"][0]["inspection_id"] == created["inspection_id"]
