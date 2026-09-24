import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError


class ReservationConflict(Exception):
    def __init__(self, response: dict[str, str]):
        self.response = response


def get_activity(engine: Engine, activity_id: str) -> dict[str, object] | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT activity_id, name, starts_at, ends_at, capacity, reserved_count "
                "FROM activities WHERE activity_id = :activity_id"
            ),
            {"activity_id": activity_id},
        ).mappings().first()
    if row is None:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    starts_at = row["starts_at"]
    ends_at = row["ends_at"]
    status = "not_started" if now < starts_at else "ended" if now >= ends_at else "active"
    return {**dict(row), "status": status, "remaining_capacity": row["capacity"] - row["reserved_count"]}


def reserve(
    engine: Engine,
    activity_id: str,
    user_id: str,
    idempotency_key: str,
) -> tuple[int, dict[str, str]]:
    fingerprint = hashlib.sha256(json.dumps({"user_id": user_id}, sort_keys=True).encode()).hexdigest()
    with engine.begin() as connection:
        # 活动行锁串行化同一活动的预约，随后读取幂等记录可看到前一事务结果。
        activity = connection.execute(
            text("SELECT starts_at, ends_at FROM activities WHERE activity_id = :activity_id FOR UPDATE"),
            {"activity_id": activity_id},
        ).mappings().first()
        if activity is None:
            return 404, {"code": "activity_not_found", "message": "活动不存在"}

        previous = connection.execute(
            text(
                "SELECT request_fingerprint, response_json, http_status "
                "FROM idempotency_records "
                "WHERE activity_id = :activity_id AND idempotency_key = :idempotency_key"
            ),
            {"activity_id": activity_id, "idempotency_key": idempotency_key},
        ).mappings().first()
        if previous is not None:
            if previous["request_fingerprint"] != fingerprint:
                return 409, {"code": "idempotency_key_conflict", "message": "幂等键已用于其他请求"}
            return int(previous["http_status"]), json.loads(previous["response_json"])

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if now < activity["starts_at"]:
            return 409, {"code": "activity_not_started", "message": "当前活动状态不允许预约"}
        if now >= activity["ends_at"]:
            return 409, {"code": "activity_ended", "message": "当前活动状态不允许预约"}

        updated = connection.execute(
            text(
                "UPDATE activities SET reserved_count = reserved_count + 1 "
                "WHERE activity_id = :activity_id AND reserved_count < capacity"
            ),
            {"activity_id": activity_id},
        )
        if updated.rowcount != 1:
            return 409, {"code": "capacity_exhausted", "message": "活动名额已满"}

        try:
            connection.execute(
                text("INSERT INTO reservations (activity_id, user_id) VALUES (:activity_id, :user_id)"),
                {"activity_id": activity_id, "user_id": user_id},
            )
        except IntegrityError as exc:
            # 抛出事务外异常，确保前面的容量计数也一并回滚。
            raise ReservationConflict({"code": "already_reserved", "message": "用户已经预约过"}) from exc

        response = {"activity_id": activity_id, "user_id": user_id, "status": "reserved"}
        connection.execute(
            text(
                "INSERT INTO idempotency_records "
                "(activity_id, idempotency_key, request_fingerprint, http_status, response_json) "
                "VALUES (:activity_id, :idempotency_key, :fingerprint, 201, :response_json)"
            ),
            {
                "activity_id": activity_id,
                "idempotency_key": idempotency_key,
                "fingerprint": fingerprint,
                "response_json": json.dumps(response, ensure_ascii=False),
            },
        )
        return 201, response
