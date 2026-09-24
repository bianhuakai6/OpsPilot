from dataclasses import dataclass, field
from datetime import datetime, timezone

from pydantic import BaseModel, Field


# 活动与预约数据模型
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
