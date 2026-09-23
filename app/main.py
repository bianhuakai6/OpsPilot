from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="OpsPilot", version="0.1.0")


@dataclass
class Activity:
    activity_id: str
    name: str
    starts_at: datetime
    ends_at: datetime
    capacity: int
    reservations: set[str] = field(default_factory=set)

    @property
    def remaining_capacity(self) -> int:
        return self.capacity - len(self.reservations)

    def status(self, now: datetime | None = None) -> str:
        current = now or datetime.now(timezone.utc)
        if current < self.starts_at:
            return "not_started"
        if current >= self.ends_at:
            return "ended"
        return "active"


class ReservationRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)


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
    """重置演示数据，保证测试和本地实验可重复。"""
    with state_lock:
        activities.clear()
        activities.update(_default_activities())
        idempotency_records.clear()


def _get_activity(activity_id: str) -> Activity:
    activity = activities.get(activity_id)
    if activity is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "activity_not_found", "message": "活动不存在"},
        )
    return activity


@app.get("/healthz", tags=["system"])
def healthz() -> dict[str, str]:
    """提供进程级健康状态，供本地和容器检查使用。"""
    return {"status": "ok"}


@app.get("/api/v1/activities/{activity_id}", tags=["activities"])
def get_activity(activity_id: str) -> dict[str, object]:
    activity = _get_activity(activity_id)
    return {
        "activity_id": activity.activity_id,
        "name": activity.name,
        "status": activity.status(),
        "capacity": activity.capacity,
        "remaining_capacity": activity.remaining_capacity,
        "starts_at": activity.starts_at,
        "ends_at": activity.ends_at,
    }


@app.post("/api/v1/activities/{activity_id}/reservations", status_code=201, tags=["activities"])
def reserve(
    activity_id: str,
    request: ReservationRequest,
    idempotency_key: str = Header(min_length=1, max_length=128, alias="Idempotency-Key"),
) -> dict[str, str]:
    # 检查和写入必须在同一临界区；当前锁只保证单进程线程安全。
    with state_lock:
        activity = _get_activity(activity_id)
        record_key = (activity_id, idempotency_key)

        # 重试复用同一键时返回原结果；同一键绑定不同用户则视为客户端冲突。
        previous = idempotency_records.get(record_key)
        if previous is not None:
            previous_user_id, previous_response = previous
            if previous_user_id != request.user_id:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "idempotency_key_conflict", "message": "幂等键已用于其他用户"},
                )
            return previous_response

        status = activity.status()
        if status != "active":
            raise HTTPException(
                status_code=409,
                detail={"code": f"activity_{status}", "message": "当前活动状态不允许预约"},
            )
        if request.user_id in activity.reservations:
            raise HTTPException(
                status_code=409,
                detail={"code": "already_reserved", "message": "用户已经预约过"},
            )
        if activity.remaining_capacity <= 0:
            raise HTTPException(
                status_code=409,
                detail={"code": "capacity_exhausted", "message": "活动名额已满"},
            )

        activity.reservations.add(request.user_id)
        response = {
            "activity_id": activity_id,
            "user_id": request.user_id,
            "status": "reserved",
        }
        idempotency_records[record_key] = (request.user_id, response)
        return response
