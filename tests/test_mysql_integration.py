import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.config import Settings
from app.database import create_database_engine
from app.inspection_store import ensure_inspection_tables, load_inspection_history, save_inspection
from app.mysql_store import ReservationConflict, reserve


pytestmark = pytest.mark.mysql


@pytest.fixture()
def mysql_engine():
    if os.getenv("OPSPILOT_RUN_MYSQL_TESTS") != "1":
        pytest.skip("set OPSPILOT_RUN_MYSQL_TESTS=1 to run MySQL integration tests")
    engine = create_database_engine(Settings(database_url="mysql+pymysql://opspilot:opspilot_local_password@127.0.0.1:3306/opspilot"))
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM idempotency_records WHERE activity_id = 'activity-001'"))
        connection.execute(text("DELETE FROM reservations WHERE activity_id = 'activity-001'"))
        connection.execute(text("UPDATE activities SET reserved_count = 0 WHERE activity_id = 'activity-001'"))
    yield engine
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM idempotency_records WHERE activity_id = 'activity-001'"))
        connection.execute(text("DELETE FROM reservations WHERE activity_id = 'activity-001'"))
        connection.execute(text("UPDATE activities SET reserved_count = 0 WHERE activity_id = 'activity-001'"))
    engine.dispose()


def test_mysql_concurrent_reservations_do_not_oversell(mysql_engine) -> None:
    def submit(index: int) -> int:
        try:
            return reserve(mysql_engine, "activity-001", f"mysql-concurrent-{index}", f"mysql-key-{index}")[0]
        except ReservationConflict:
            return 409

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = list(executor.map(submit, range(8)))

    assert statuses.count(201) == 2
    assert statuses.count(409) == 6


def test_mysql_idempotency_retry_does_not_create_second_reservation(mysql_engine) -> None:
    first = reserve(mysql_engine, "activity-001", "mysql-retry-user", "mysql-retry-key")
    retry = reserve(mysql_engine, "activity-001", "mysql-retry-user", "mysql-retry-key")

    assert first == retry
    with mysql_engine.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM reservations WHERE activity_id = 'activity-001' AND user_id = 'mysql-retry-user'")
        ).scalar_one()
    assert count == 1


def test_mysql_duplicate_user_does_not_leak_capacity(mysql_engine) -> None:
    reserve(mysql_engine, "activity-001", "mysql-duplicate-user", "mysql-duplicate-key-1")
    with pytest.raises(ReservationConflict):
        reserve(mysql_engine, "activity-001", "mysql-duplicate-user", "mysql-duplicate-key-2")

    with mysql_engine.connect() as connection:
        reserved_count = connection.execute(
            text("SELECT reserved_count FROM activities WHERE activity_id = 'activity-001'")
        ).scalar_one()
    assert reserved_count == 1


def test_mysql_inspection_history_persists_reports_and_checks(mysql_engine) -> None:
    inspection_ids = ["test-inspection-history-old", "test-inspection-history-new"]
    ensure_inspection_tables(mysql_engine)
    with mysql_engine.begin() as connection:
        connection.execute(
            text("DELETE FROM inspection_checks WHERE inspection_id IN (:old_id, :new_id)"),
            {"old_id": inspection_ids[0], "new_id": inspection_ids[1]},
        )
        connection.execute(
            text("DELETE FROM inspection_runs WHERE inspection_id IN (:old_id, :new_id)"),
            {"old_id": inspection_ids[0], "new_id": inspection_ids[1]},
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    reports = [
        {
            "inspection_id": inspection_ids[0],
            "environment": "test",
            "status": "pass",
            "checked_at": now,
            "checks": [{
                "check_id": "mysql_connectivity",
                "status": "pass",
                "severity": "info",
                "evidence": "SELECT 1 成功",
                "recommendation": "无需处理",
            }],
        },
        {
            "inspection_id": inspection_ids[1],
            "environment": "test",
            "status": "fail",
            "checked_at": now + timedelta(seconds=1),
            "checks": [{
                "check_id": "redis_connectivity",
                "status": "fail",
                "severity": "warning",
                "evidence": "测试证据",
                "recommendation": "检查 Redis",
            }],
        },
    ]

    try:
        for report in reports:
            save_inspection(mysql_engine, report)

        history = load_inspection_history(mysql_engine, limit=2)

        assert [item["inspection_id"] for item in history] == [inspection_ids[1], inspection_ids[0]]
        assert history[0]["status"] == "fail"
        assert history[0]["checks"] == [{
            "check_id": "redis_connectivity",
            "status": "fail",
            "severity": "warning",
            "evidence": "测试证据",
            "recommendation": "检查 Redis",
        }]
    finally:
        # 仅删除本测试使用的 ID，避免影响本地已有巡检历史。
        with mysql_engine.begin() as connection:
            connection.execute(
                text("DELETE FROM inspection_checks WHERE inspection_id IN (:old_id, :new_id)"),
                {"old_id": inspection_ids[0], "new_id": inspection_ids[1]},
            )
            connection.execute(
                text("DELETE FROM inspection_runs WHERE inspection_id IN (:old_id, :new_id)"),
                {"old_id": inspection_ids[0], "new_id": inspection_ids[1]},
            )
