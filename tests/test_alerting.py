from app.alerting import InspectionAlertStore


def _report(inspection_id: str, status: str) -> dict[str, object]:
    return {
        "inspection_id": inspection_id,
        "checks": [{
            "check_id": "mysql_connectivity",
            "status": status,
            "severity": "critical" if status == "fail" else "info",
            "evidence": "连接异常" if status == "fail" else "SELECT 1 返回成功",
            "recommendation": "检查 MySQL" if status == "fail" else "无需处理",
        }],
    }


def test_repeated_inspection_failures_update_the_same_alert() -> None:
    store = InspectionAlertStore()

    first = store.reconcile(_report("inspection-1", "fail"))[0]
    second = store.reconcile(_report("inspection-2", "fail"))[0]

    assert first["alert_id"] == second["alert_id"]
    assert second["occurrences"] == 2
    assert second["source_inspection_id"] == "inspection-2"
    assert len(store.list_events(include_resolved=False)) == 1


def test_passing_check_resolves_the_open_alert() -> None:
    store = InspectionAlertStore()
    opened = store.reconcile(_report("inspection-1", "fail"))[0]

    resolved = store.reconcile(_report("inspection-2", "pass"))[0]

    assert resolved["alert_id"] == opened["alert_id"]
    assert resolved["status"] == "resolved"
    assert resolved["resolved_at"] is not None
    assert store.list_events(include_resolved=False) == []


def test_skipped_check_does_not_resolve_an_open_alert() -> None:
    store = InspectionAlertStore()
    store.reconcile(_report("inspection-1", "fail"))
    skipped = store.reconcile(_report("inspection-2", "skipped"))

    assert skipped == []
    assert store.list_events(include_resolved=False)[0]["status"] == "open"
