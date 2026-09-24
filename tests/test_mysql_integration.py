import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

from app.config import Settings
from app.database import create_database_engine
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
