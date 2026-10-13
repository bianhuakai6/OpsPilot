from fastapi import APIRouter, HTTPException

from app.alerting import alert_event_store
from app.runbooks import get_runbook_for_check

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


# 展示巡检关联出来的本地告警事件，不执行自动修复。
@router.get("")
def list_alerts() -> dict[str, list[dict[str, object]]]:
    return {"items": alert_event_store.list_events()}


@router.get("/{alert_id}/runbook")
def recommend_runbook(alert_id: str) -> dict[str, object]:
    event = alert_event_store.get_event(alert_id)
    if event is None:
        raise HTTPException(status_code=404, detail={"code": "alert_not_found"})
    runbook = get_runbook_for_check(str(event["check_id"]))
    if runbook is None:
        raise HTTPException(status_code=404, detail={"code": "runbook_not_found"})
    return {
        "match": "exact_check_id",
        "alert": event,
        "runbook": runbook,
        "execution": {"executed": False, "requires_human_approval": True},
    }
