from fastapi.testclient import TestClient

from app.alerting import InspectionAlertStore
from app.main import app
from app.routes import alerts


def test_alert_endpoint_lists_correlated_events(monkeypatch) -> None:
    store = InspectionAlertStore()
    store.reconcile({
        "inspection_id": "inspection-api-test",
        "checks": [{
            "check_id": "redis_connectivity",
            "status": "fail",
            "severity": "warning",
            "evidence": "PING 超时",
            "recommendation": "检查 Redis 服务",
        }],
    })
    monkeypatch.setattr(alerts, "alert_event_store", store)

    response = TestClient(app).get("/api/v1/alerts")

    assert response.status_code == 200
    assert response.json()["items"][0]["source_inspection_id"] == "inspection-api-test"
