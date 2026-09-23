from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="OpsPilot", version="0.1.0")


@dataclass
class Activity:
    activity_id: str
    name: str
    starts_at: datetime
    ends_at: datetime
    capacity: int
    registrations: set[str] = field(default_factory=set)

    @property
    def remaining_capacity(self) -> int:
        return self.capacity - len(self.registrations)

    def status(self, now: datetime | None = None) -> str:
        current = now or datetime.now(timezone.utc)
        if current < self.starts_at:
            return "not_started"
        if current >= self.ends_at:
            return "ended"
        return "active"


class RegistrationRequest(BaseModel):
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


def reset_state() -> None:
    """Reset local demo data for tests and repeatable development runs."""
    activities.clear()
    activities.update(_default_activities())


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
    """Return a process-level health response for local and container checks."""
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


@app.post("/api/v1/activities/{activity_id}/registrations", status_code=201, tags=["activities"])
def register(activity_id: str, request: RegistrationRequest) -> dict[str, str]:
    activity = _get_activity(activity_id)
    status = activity.status()
    if status != "active":
        raise HTTPException(
            status_code=409,
            detail={"code": f"activity_{status}", "message": "当前活动状态不允许预约"},
        )
    if request.user_id in activity.registrations:
        raise HTTPException(
            status_code=409,
            detail={"code": "already_registered", "message": "用户已经预约过"},
        )
    if activity.remaining_capacity <= 0:
        raise HTTPException(
            status_code=409,
            detail={"code": "capacity_exhausted", "message": "活动名额已满"},
        )

    activity.registrations.add(request.user_id)
    return {
        "activity_id": activity_id,
        "user_id": request.user_id,
        "status": "registered",
    }
