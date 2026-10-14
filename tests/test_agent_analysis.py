from fastapi.testclient import TestClient

from app.alerting import InspectionAlertStore
from app.main import app
from app.model_client import ModelClientError
from app.routes import agent_analysis


def test_analysis_requires_alert_and_model(monkeypatch) -> None:
    store = InspectionAlertStore()
    event = store.reconcile({
        "inspection_id": "analysis-test",
        "checks": [{"check_id": "redis_connectivity", "status": "fail", "severity": "warning", "evidence": "断开", "recommendation": "检查 Redis"}],
    })[0]
    monkeypatch.setattr(agent_analysis, "alert_event_store", store)
    monkeypatch.setattr(agent_analysis, "request_response", lambda *args, **kwargs: (_ for _ in ()).throw(ModelClientError("OPSPILOT_MODEL_API_KEY 未配置")))

    response = TestClient(app).post(f"/api/v1/agent/analyze/{event['alert_id']}")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "model_unavailable"
