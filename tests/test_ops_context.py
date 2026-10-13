from fastapi.testclient import TestClient

from app.alerting import InspectionAlertStore
from app.main import app
from app.routes import ops_context


def test_alert_context_aggregates_read_only_evidence(monkeypatch) -> None:
    store = InspectionAlertStore()
    event = store.reconcile({
        "inspection_id": "inspection-context-test",
        "checks": [{
            "check_id": "mysql_connectivity",
            "status": "fail",
            "severity": "critical",
            "evidence": "连接异常",
            "recommendation": "检查 MySQL",
        }],
    })[0]
    monkeypatch.setattr(ops_context, "alert_event_store", store)

    response = TestClient(app).get(f"/api/v1/ops-context/alerts/{event['alert_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["context_version"] == "m5.v1"
    assert body["alert"]["check_id"] == "mysql_connectivity"
    assert body["runbook"]["runbook_id"] == "mysql-connectivity"
    assert body["evidence"]["source_inspection_id"] == "inspection-context-test"
    assert body["agent_boundary"] == {
        "read_only": True,
        "commands_executed": False,
        "external_model_called": False,
        "human_approval_required_for_actions": True,
    }


def test_alert_context_returns_404_for_unknown_alert() -> None:
    response = TestClient(app).get("/api/v1/ops-context/alerts/missing")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "alert_not_found"
