from fastapi import APIRouter


router = APIRouter(tags=["system"])


# 健康检查接口
@router.get("/healthz")
def healthz() -> dict[str, str]:
    """提供进程级存活状态，供本地和容器探针使用。"""
    return {"status": "ok"}
