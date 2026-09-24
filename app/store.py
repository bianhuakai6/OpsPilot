from datetime import datetime, timezone
from threading import Lock

from fastapi import HTTPException

from app.models import Activity


# 内存状态存储
def _default_activities() -> dict[str, Activity]:
    return {
        "activity-001": Activity(
            activity_id="activity-001",
            name="云平台实践资源预约",
            starts_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ends_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            capacity=2,
        )
    }


activities = _default_activities()
idempotency_records: dict[tuple[str, str], tuple[str, dict[str, str]]] = {}
state_lock = Lock()


def reset_state() -> None:
    """重置演示数据，保证测试和本地验收可以重复执行。"""
    with state_lock:
        activities.clear()
        activities.update(_default_activities())
        idempotency_records.clear()


def get_activity(activity_id: str) -> Activity:
    activity = activities.get(activity_id)
    if activity is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "activity_not_found", "message": "活动不存在"},
        )
    return activity
