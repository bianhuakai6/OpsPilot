"""受限只读运维工具：为 Agent 提供固定能力，不开放任意命令执行。"""

import json
from pathlib import Path
from typing import Any

from app.alerting import alert_event_store
from app.inspection import get_inspection_history
from app.inspection_store import load_inspection_history
from app.runtime import database_engine
from app.slo import slo_snapshot


MAX_LIMIT = 20
RELEASE_HISTORY_PATH = Path(__file__).resolve().parents[1] / "data" / "release-history.jsonl"

TOOL_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "name": "list_alerts",
        "description": "读取当前进程内的巡检关联告警",
        "parameters": {"limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT}},
        "read_only": True,
    },
    {
        "name": "latest_inspections",
        "description": "读取最近的结构化巡检结果",
        "parameters": {"limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT}},
        "read_only": True,
    },
    {
        "name": "slo_snapshot",
        "description": "读取当前进程生命周期的 SLO 快照",
        "parameters": {},
        "read_only": True,
    },
    {
        "name": "release_history",
        "description": "读取本机发布和回滚的安全元数据",
        "parameters": {"limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT}},
        "read_only": True,
    },
)


def list_tools() -> list[dict[str, Any]]:
    return [dict(tool) for tool in TOOL_CATALOG]


def _bounded_limit(limit: int) -> int:
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit 必须在 1 到 {MAX_LIMIT} 之间")
    return limit


def _release_history(limit: int) -> dict[str, Any]:
    if not RELEASE_HISTORY_PATH.exists():
        return {"available": False, "source": "host_release_history_not_mounted", "items": []}
    records: list[dict[str, Any]] = []
    for line in RELEASE_HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        # 只允许发布元数据进入 Agent 上下文，不传播异常原文或环境变量。
        records.append({key: raw.get(key) for key in (
            "recorded_at_utc", "action", "status", "version", "git_sha", "image", "stage", "readiness"
        )})
    return {"available": True, "source": "data/release-history.jsonl", "items": records[-limit:][::-1]}


def call_tool(name: str, *, limit: int = 10) -> dict[str, Any]:
    """调用固定白名单工具；未知工具和越界参数直接拒绝。"""
    if name == "list_alerts":
        return {"items": alert_event_store.list_events()[:_bounded_limit(limit)]}
    if name == "latest_inspections":
        bounded = _bounded_limit(limit)
        items = load_inspection_history(database_engine, bounded) if database_engine is not None else get_inspection_history()[:bounded]
        return {"items": items}
    if name == "slo_snapshot":
        return slo_snapshot()
    if name == "release_history":
        return _release_history(_bounded_limit(limit))
    raise KeyError(f"unknown_tool:{name}")
