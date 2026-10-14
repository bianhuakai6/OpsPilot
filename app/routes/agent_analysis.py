import json

from fastapi import APIRouter, HTTPException

from app.alerting import alert_event_store
from app.config import Settings
from app.model_client import ModelClientError, request_response
from app.runbooks import get_runbook_for_check
from app.slo import slo_snapshot


router = APIRouter(prefix="/api/v1/agent", tags=["agent-analysis"])


def _analysis_prompt(alert: dict[str, object]) -> str:
    context = {
        "alert": alert,
        "runbook": get_runbook_for_check(str(alert["check_id"])),
        "slo": slo_snapshot(),
    }
    return (
        "你是只读 SRE 分析助手。只能基于给定证据提出候选，不得声称已执行命令或确认唯一根因。"
        "请用 JSON 返回 root_cause_candidates、evidence、recommended_checks、risk_level、"
        "requires_human_approval 五个字段。不得输出自动修复命令。\n"
        + json.dumps(context, ensure_ascii=False, default=str)
    )


@router.post("/analyze/{alert_id}")
def analyze_alert(alert_id: str) -> dict[str, object]:
    alert = alert_event_store.get_event(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail={"code": "alert_not_found"})
    try:
        result = request_response(_analysis_prompt(alert), Settings.from_env())
    except ModelClientError as exc:
        raise HTTPException(status_code=503, detail={"code": "model_unavailable", "message": str(exc)})
    return {
        "analysis_status": "completed",
        "alert_id": alert_id,
        "model": result["model"],
        "response_id": result["response_id"],
        "text": result["text"],
        "boundary": {"read_only": True, "commands_executed": False, "human_approval_required": True},
    }
