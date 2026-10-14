import json

from fastapi import APIRouter, HTTPException

from app.alerting import alert_event_store
from app.config import Settings
from app.model_client import ModelClientError, request_response
from app.runbooks import get_runbook_for_check
from app.slo import slo_snapshot


router = APIRouter(prefix="/api/v1/agent", tags=["agent-analysis"])

REQUIRED_ANALYSIS_FIELDS = (
    "root_cause_candidates", "evidence", "recommended_checks", "risk_level", "requires_human_approval"
)


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


def _parse_analysis(text: str) -> dict[str, object]:
    """只接受对象 JSON，避免把任意模型散文当作可信运维结论。"""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModelClientError("模型分析不是有效 JSON") from exc
    if not isinstance(parsed, dict) or any(field not in parsed for field in REQUIRED_ANALYSIS_FIELDS):
        raise ModelClientError("模型分析缺少必需字段")
    if parsed["requires_human_approval"] is not True:
        raise ModelClientError("模型分析未声明人工审批")
    return parsed


@router.post("/analyze/{alert_id}")
def analyze_alert(alert_id: str) -> dict[str, object]:
    alert = alert_event_store.get_event(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail={"code": "alert_not_found"})
    try:
        result = request_response(_analysis_prompt(alert), Settings.from_env())
    except ModelClientError as exc:
        raise HTTPException(status_code=503, detail={"code": "model_unavailable", "message": str(exc)})
    try:
        analysis = _parse_analysis(result["text"])
    except ModelClientError as exc:
        raise HTTPException(status_code=502, detail={"code": "invalid_model_output", "message": str(exc)})
    return {
        "analysis_status": "completed",
        "alert_id": alert_id,
        "model": result["model"],
        "response_id": result["response_id"],
        "analysis": analysis,
        "boundary": {"read_only": True, "commands_executed": False, "human_approval_required": True},
    }
