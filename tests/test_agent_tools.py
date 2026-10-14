from fastapi.testclient import TestClient

from app.main import app


def test_tool_catalog_exposes_only_read_only_allowlist() -> None:
    body = TestClient(app).get("/api/v1/agent/tools").json()

    assert {item["name"] for item in body["items"]} == {
        "list_alerts", "latest_inspections", "slo_snapshot", "release_history"
    }
    assert body["boundary"] == {
        "read_only": True,
        "arbitrary_command_execution": False,
        "human_approval": True,
    }
    assert all(item["read_only"] is True for item in body["items"])


def test_tools_return_structured_data_and_reject_unknown_or_unsafe_arguments() -> None:
    client = TestClient(app)

    assert "items" in client.get("/api/v1/agent/tools/list_alerts").json()
    assert "items" in client.get("/api/v1/agent/tools/latest_inspections").json()
    assert "status" in client.get("/api/v1/agent/tools/slo_snapshot").json()
    assert "items" in client.get("/api/v1/agent/tools/release_history").json()
    assert client.get("/api/v1/agent/tools/exec_shell").status_code == 404
    assert client.get("/api/v1/agent/tools/list_alerts?limit=21").status_code == 422
