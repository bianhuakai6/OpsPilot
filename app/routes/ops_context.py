from fastapi import APIRouter, HTTPException

from app.alerting import alert_event_store
from app.runbooks import get_runbook_for_check
from app.slo import slo_snapshot


router = APIRouter(prefix="/api/v1/ops-context", tags=["agent-context"])


# 聚合只读上下文，给 Agent 或人工排障使用；不执行命令、不暴露连接配置。
@router.get("/alerts/{alert_id}")
def alert_context(alert_id: str) -> dict[str, object]:
    alert = alert_event_store.get_event(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail={"code": "alert_not_found"})

    runbook = get_runbook_for_check(str(alert["check_id"]))
    return {
        "context_version": "m5.v1",
        "alert": alert,
        "runbook": runbook,
        "slo": slo_snapshot(),
        "evidence": {
            "source_inspection_id": alert["source_inspection_id"],
            "check_id": alert["check_id"],
            "observed_status": alert["status"],
        },
        "agent_boundary": {
            "read_only": True,
            "commands_executed": False,
            "external_model_called": False,
            "human_approval_required_for_actions": True,
        },
    }
