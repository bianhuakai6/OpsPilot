from fastapi import APIRouter, Header, HTTPException

from app.models import ReservationRequest
from app.mysql_store import ReservationConflict, get_activity as get_mysql_activity, reserve as reserve_mysql
from app.runtime import database_engine
from app.store import activities, get_activity, idempotency_records, state_lock


router = APIRouter(prefix="/api/v1/activities", tags=["activities"])


# 活动查询接口
@router.get("/{activity_id}")
def get_activity_detail(activity_id: str) -> dict[str, object]:
    if database_engine is not None:
        activity = get_mysql_activity(database_engine, activity_id)
        if activity is None:
            raise HTTPException(status_code=404, detail={"code": "activity_not_found", "message": "活动不存在"})
        return activity

    activity = get_activity(activity_id)
    return {
        "activity_id": activity.activity_id,
        "name": activity.name,
        "status": activity.status(),
        "capacity": activity.capacity,
        "remaining_capacity": activity.remaining_capacity,
        "starts_at": activity.starts_at,
        "ends_at": activity.ends_at,
    }


# 资源预约接口
@router.post("/{activity_id}/reservations", status_code=201)
def reserve(
    activity_id: str,
    request: ReservationRequest,
    idempotency_key: str = Header(min_length=1, max_length=128, alias="Idempotency-Key"),
) -> dict[str, str]:
    if database_engine is not None:
        try:
            status_code, response = reserve_mysql(database_engine, activity_id, request.user_id, idempotency_key)
        except ReservationConflict as conflict:
            raise HTTPException(status_code=409, detail=conflict.response) from conflict
        if status_code != 201:
            raise HTTPException(status_code=status_code, detail=response)
        return response

    # 检查和写入必须在同一个临界区，避免并发请求超卖名额。
    with state_lock:
        activity = get_activity(activity_id)
        record_key = (activity_id, idempotency_key)

        # 重试复用同一键时返回原结果；同一键绑定其他用户则拒绝。
        previous = idempotency_records.get(record_key)
        if previous is not None:
            previous_user_id, previous_response = previous
            if previous_user_id != request.user_id:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "idempotency_key_conflict",
                        "message": "幂等键已用于其他用户",
                    },
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
