from app.runbooks import get_runbook, get_runbook_for_check, list_runbooks


def test_runbooks_have_safe_checks_and_manual_action_boundary() -> None:
    runbooks = list_runbooks()

    assert {item["check_id"] for item in runbooks} == {"redis_connectivity", "mysql_connectivity"}
    assert all(item["safe_checks"] for item in runbooks)
    assert all(check["kind"] in {"command", "browser"} for item in runbooks for check in item["safe_checks"])
    assert all(item["requires_human_approval"] is True for item in runbooks)
    assert all(item["forbidden_actions"] for item in runbooks)


def test_runbook_lookup_is_exact_and_unknown_check_has_no_match() -> None:
    assert get_runbook("redis-connectivity")["check_id"] == "redis_connectivity"
    assert get_runbook_for_check("mysql_connectivity")["runbook_id"] == "mysql-connectivity"
    assert get_runbook_for_check("unknown_check") is None
