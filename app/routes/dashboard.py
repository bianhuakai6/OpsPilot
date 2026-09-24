from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["dashboard"])
dashboard_file = Path(__file__).resolve().parent.parent / "static" / "dashboard.html"


# 运维控制台入口
@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard() -> HTMLResponse:
    return HTMLResponse(dashboard_file.read_text(encoding="utf-8"))
