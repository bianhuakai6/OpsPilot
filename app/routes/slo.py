from fastapi import APIRouter

from app.slo import slo_snapshot

router = APIRouter(prefix="/api/v1/slo", tags=["sre"])


# SLO 只读快照，供控制台、巡检和后续 Agent 使用。
@router.get("")
def get_slo_snapshot() -> dict[str, object]:
    return slo_snapshot()
