from fastapi import APIRouter, HTTPException, Query

from app.agent_tools import call_tool, list_tools


router = APIRouter(prefix="/api/v1/agent", tags=["agent-tools"])


# 暴露工具契约和固定只读调用入口，不提供任意 Shell 或 URL 执行能力。
@router.get("/tools")
def tool_catalog() -> dict[str, object]:
    return {
        "items": list_tools(),
        "boundary": {"read_only": True, "arbitrary_command_execution": False, "human_approval": True},
    }


@router.get("/tools/{tool_name}")
def invoke_tool(tool_name: str, limit: int = Query(default=10, ge=1, le=20)) -> dict[str, object]:
    try:
        return call_tool(tool_name, limit=limit)
    except KeyError:
        raise HTTPException(status_code=404, detail={"code": "tool_not_found"})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_tool_arguments", "message": str(exc)})
