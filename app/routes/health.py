from fastapi import APIRouter
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.database import check_database
from app.runtime import database_engine

router = APIRouter(tags=["system"])


# 健康检查接口
@router.get("/healthz")
def healthz() -> dict[str, str]:
    """提供进程级存活状态，供本地和容器探针使用。"""
    return {"status": "ok"}


# 服务就绪检查
@router.get("/readyz")
def readyz() -> dict[str, str]:
    if database_engine is not None:
        try:
            available = check_database(database_engine)
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
        if not available:
            raise HTTPException(status_code=503, detail={"code": "database_unavailable"})
    return {"status": "ready"}
