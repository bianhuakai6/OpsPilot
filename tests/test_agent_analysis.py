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


def test_analysis_rejects_unstructured_model_output() -> None:
    import pytest

    with pytest.raises(ModelClientError, match="不是有效 JSON"):
        agent_analysis._parse_analysis("不是 JSON")


def test_analysis_requires_human_approval_in_model_output() -> None:
    import pytest

    payload = '{"root_cause_candidates": [], "evidence": [], "recommended_checks": [], "risk_level": "low", "requires_human_approval": false}'
    with pytest.raises(ModelClientError, match="人工审批"):
        agent_analysis._parse_analysis(payload)


def test_analysis_requires_evidence_and_candidate_lists() -> None:
    import pytest

    payload = '{"root_cause_candidates": [], "evidence": [], "recommended_checks": [], "risk_level": "low", "requires_human_approval": true}'
    with pytest.raises(ModelClientError, match="根因候选"):
        agent_analysis._parse_analysis(payload)
