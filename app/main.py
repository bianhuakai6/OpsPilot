from fastapi import FastAPI

from app.config import Settings
from app.models import Activity, ReservationRequest
from app.routes.activities import router as activities_router
from app.routes.health import router as health_router
from app.store import activities, reset_state


# 应用组装入口
settings = Settings.from_env()
app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(health_router)
app.include_router(activities_router)


# 兼容学习阶段的导入路径，测试仍可从 app.main 获取核心对象。
__all__ = ["Activity", "ReservationRequest", "activities", "app", "reset_state", "settings"]
