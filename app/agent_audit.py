"""Agent 分析审计：只保留请求结果元数据，不保存密钥和完整模型原文。"""

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4


class AgentAuditStore:
    def __init__(self, maxlen: int = 100) -> None:
        self._lock = Lock()
        self._events: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def record(self, *, alert_id: str, model: str, status: str, reason: str | None = None) -> dict[str, Any]:
        event = {
            "audit_id": f"agent-audit-{uuid4()}",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "alert_id": alert_id,
            "model": model,
            "status": status,
            "reason": reason,
        }
        with self._lock:
            self._events.appendleft(event)
        return dict(event)

    def list_events(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in list(self._events)[:limit]]


agent_audit_store = AgentAuditStore()
