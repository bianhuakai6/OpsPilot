from fastapi.testclient import TestClient

from app.alerting import InspectionAlertStore
from app.main import app
from app.routes import alerts


def test_runbook_list_and_details_are_read_only() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/runbooks")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    assert client.get("/api/v1/runbooks/redis-connectivity").status_code == 200
    assert client.get("/api/v1/runbooks/missing").status_code == 404


def test_alert_recommendation_matches_check_and_never_executes(monkeypatch) -> None:
    store = InspectionAlertStore()
    event = store.reconcile({
        "inspection_id": "inspection-runbook-test",
        "checks": [{
            "check_id": "redis_connectivity",
            "status": "fail",
            "severity": "warning",
            "evidence": "ConnectionError",
            "recommendation": "检查 Redis",
        }],
    })[0]
    monkeypatch.setattr(alerts, "alert_event_store", store)

    response = TestClient(app).get(f"/api/v1/alerts/{event['alert_id']}/runbook")

    assert response.status_code == 200
    body = response.json()
    assert body["match"] == "exact_check_id"
    assert body["runbook"]["runbook_id"] == "redis-connectivity"
    assert body["execution"] == {"executed": False, "requires_human_approval": True}


def test_alert_recommendation_reports_missing_mapping(monkeypatch) -> None:
    store = InspectionAlertStore()
    event = store.reconcile({
        "inspection_id": "inspection-unmapped-test",
        "checks": [{
            "check_id": "disk_space",
            "status": "fail",
            "severity": "critical",
            "evidence": "可用空间不足",
            "recommendation": "检查磁盘",
        }],
    })[0]
    monkeypatch.setattr(alerts, "alert_event_store", store)

    response = TestClient(app).get(f"/api/v1/alerts/{event['alert_id']}/runbook")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "runbook_not_found"
