from fastapi import FastAPI

from app.logging_config import configure_logging
from app.middleware import RequestLoggingMiddleware
from app.models import Activity, ReservationRequest
from app.routes.activities import router as activities_router
from app.routes.health import router as health_router
from app.routes.inspections import router as inspections_router
from app.routes.dashboard import router as dashboard_router
from app.routes.load_testing import router as load_testing_router
from app.runtime import database_engine, settings
from app.store import activities, reset_state


# 应用组装入口
# 应用组装入口
configure_logging()
app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(health_router)
app.include_router(activities_router)
app.include_router(inspections_router)
app.include_router(dashboard_router)
app.include_router(load_testing_router)


# 兼容学习阶段的导入路径，测试仍可从 app.main 获取核心对象。
__all__ = ["Activity", "ReservationRequest", "activities", "app", "reset_state", "settings"]
