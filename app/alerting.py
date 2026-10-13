from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4


class InspectionAlertStore:
    """把巡检失败关联为本进程内的告警事件，便于本地验证状态流转。"""

    def __init__(self) -> None:
        self._lock = Lock()
        self._events: dict[str, dict[str, Any]] = {}

    def reconcile(self, report: dict[str, Any]) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        inspection_id = str(report["inspection_id"])
        with self._lock:
            correlated: list[dict[str, Any]] = []
            for check in report["checks"]:
                check_id = str(check["check_id"])
                event = self._events.get(check_id)
                if check["status"] == "fail":
                    if event is None:
                        event = {
                            "alert_id": f"alert-{uuid4()}",
                            "check_id": check_id,
                            "status": "open",
                            "first_seen_at": now,
                            "occurrences": 0,
                        }
                        self._events[check_id] = event
                    event.update({
                        "status": "open",
                        "severity": check["severity"],
                        "evidence": check["evidence"],
                        "recommendation": check["recommendation"],
                        "source_inspection_id": inspection_id,
                        "last_seen_at": now,
                        "resolved_at": None,
                        "occurrences": int(event["occurrences"]) + 1,
                    })
                    correlated.append(dict(event))
                elif check["status"] == "pass" and event is not None and event["status"] == "open":
                    event.update({
                        "status": "resolved",
                        "source_inspection_id": inspection_id,
                        "last_seen_at": now,
                        "resolved_at": now,
                    })
                    correlated.append(dict(event))
            return correlated

    def list_events(self, include_resolved: bool = True) -> list[dict[str, Any]]:
        with self._lock:
            events = [dict(event) for event in self._events.values()]
        if not include_resolved:
            events = [event for event in events if event["status"] == "open"]
        return sorted(events, key=lambda event: event["last_seen_at"], reverse=True)


alert_event_store = InspectionAlertStore()
