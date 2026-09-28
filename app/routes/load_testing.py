from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.load_testing import MAX_DURATION_SECONDS, MAX_WORKERS, load_test_manager


router = APIRouter(prefix="/api/v1/load-tests", tags=["load-tests"])


class LoadTestRequest(BaseModel):
    target: Literal["health", "readiness", "activity"]
    duration_seconds: int = Field(ge=1, le=MAX_DURATION_SECONDS)
    workers: int = Field(ge=1, le=MAX_WORKERS)


@router.post("")
def start_load_test(request: LoadTestRequest) -> dict[str, object]:
    try:
        task = load_test_manager.start(request.target, request.duration_seconds, request.workers)
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail={"code": str(error)}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": str(error)}) from error
    return task


@router.get("/current")
def current_load_test() -> dict[str, object]:
    return {"task": load_test_manager.snapshot()}


@router.post("/stop")
def stop_load_test() -> dict[str, object]:
    task = load_test_manager.stop()
    if task is None:
        raise HTTPException(status_code=404, detail={"code": "task_not_found"})
    return task
