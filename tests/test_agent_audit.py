from fastapi.testclient import TestClient

from app.agent_audit import AgentAuditStore
from app.main import app


def test_audit_store_keeps_bounded_metadata() -> None:
    store = AgentAuditStore(maxlen=1)
    store.record(alert_id="a1", model="test", status="completed")
    event = store.record(alert_id="a2", model="test", status="failed", reason="model_unavailable")

    assert store.list_events() == [event]
    assert "prompt" not in event
    assert "api_key" not in event


def test_audit_endpoint_is_bounded() -> None:
    response = TestClient(app).get("/api/v1/agent/audit?limit=21")

    assert response.status_code == 422
