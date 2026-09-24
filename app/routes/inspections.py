from fastapi import APIRouter

from app.inspection import get_inspection_history, run_inspection


router = APIRouter(prefix="/api/v1/inspections", tags=["inspections"])


# 自动化巡检接口
@router.post("/run")
def run_inspection_endpoint() -> dict[str, object]:
    return run_inspection()


@router.get("/history")
def inspection_history_endpoint() -> dict[str, object]:
    return {"items": get_inspection_history()}
