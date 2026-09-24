from fastapi import APIRouter

from app.inspection import run_inspection


router = APIRouter(prefix="/api/v1/inspections", tags=["inspections"])


# 自动化巡检接口
@router.post("/run")
def run_inspection_endpoint() -> dict[str, object]:
    return run_inspection()
