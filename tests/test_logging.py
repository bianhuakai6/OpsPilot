from fastapi.testclient import TestClient

from app.main import app


def test_request_id_is_returned_and_can_be_provided() -> None:
    response = TestClient(app).get("/healthz", headers={"X-Request-ID": "learning-request-001"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "learning-request-001"
