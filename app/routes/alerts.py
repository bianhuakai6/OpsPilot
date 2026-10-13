from fastapi import APIRouter

from app.alerting import alert_event_store

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


# 展示巡检关联出来的本地告警事件，不执行自动修复。
@router.get("")
def list_alerts() -> dict[str, list[dict[str, object]]]:
    return {"items": alert_event_store.list_events()}
