from fastapi import APIRouter, HTTPException

from app.runbooks import get_runbook, list_runbooks

router = APIRouter(prefix="/api/v1/runbooks", tags=["runbooks"])


# 提供可复用的结构化排障流程，接口只读，不会执行其中的命令。
@router.get("")
def runbook_list() -> dict[str, list[dict[str, object]]]:
    return {"items": list_runbooks()}


@router.get("/{runbook_id}")
def runbook_detail(runbook_id: str) -> dict[str, object]:
    runbook = get_runbook(runbook_id)
    if runbook is None:
        raise HTTPException(status_code=404, detail={"code": "runbook_not_found"})
    return runbook
