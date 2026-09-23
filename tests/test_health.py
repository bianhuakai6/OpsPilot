from fastapi.testclient import TestClient

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.main import Activity, activities, app, reset_state


client = TestClient(app)


def setup_function() -> None:
    reset_state()


def test_healthz_returns_ok() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_activity_returns_current_capacity() -> None:
    response = client.get("/api/v1/activities/activity-001")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["capacity"] == 2
    assert body["remaining_capacity"] == 2


def test_get_missing_activity_returns_stable_error() -> None:
    response = client.get("/api/v1/activities/missing")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "activity_not_found"


def test_reserve_succeeds_and_reduces_capacity() -> None:
    response = client.post(
        "/api/v1/activities/activity-001/reservations",
        json={"user_id": "user-001"},
        headers={"Idempotency-Key": "request-001"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "reserved"
    assert client.get("/api/v1/activities/activity-001").json()["remaining_capacity"] == 1


def test_duplicate_reservation_is_rejected() -> None:
    endpoint = "/api/v1/activities/activity-001/reservations"
    client.post(endpoint, json={"user_id": "user-001"}, headers={"Idempotency-Key": "request-001"})

    response = client.post(
        endpoint,
        json={"user_id": "user-001"},
        headers={"Idempotency-Key": "request-002"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "already_reserved"


def test_capacity_exhaustion_is_rejected() -> None:
    endpoint = "/api/v1/activities/activity-001/reservations"
    client.post(endpoint, json={"user_id": "user-001"}, headers={"Idempotency-Key": "request-001"})
    client.post(endpoint, json={"user_id": "user-002"}, headers={"Idempotency-Key": "request-002"})

    response = client.post(
        endpoint,
        json={"user_id": "user-003"},
        headers={"Idempotency-Key": "request-003"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "capacity_exhausted"


def test_empty_user_id_is_rejected() -> None:
    response = client.post(
        "/api/v1/activities/activity-001/reservations",
        json={"user_id": ""},
    )

    assert response.status_code == 422


def test_missing_idempotency_key_is_rejected() -> None:
    response = client.post(
        "/api/v1/activities/activity-001/reservations",
        json={"user_id": "user-001"},
    )

    assert response.status_code == 422


def test_reservation_before_start_is_rejected() -> None:
    activities["activity-001"] = Activity(
        activity_id="activity-001",
        name="未来活动",
        starts_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        ends_at=datetime(2099, 1, 2, tzinfo=timezone.utc),
        capacity=1,
    )

    response = client.post(
        "/api/v1/activities/activity-001/reservations",
        json={"user_id": "user-001"},
        headers={"Idempotency-Key": "request-001"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "activity_not_started"


def test_reservation_after_end_is_rejected() -> None:
    activities["activity-001"] = Activity(
        activity_id="activity-001",
        name="已结束活动",
        starts_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        ends_at=datetime(2020, 1, 2, tzinfo=timezone.utc),
        capacity=1,
    )

    response = client.post(
        "/api/v1/activities/activity-001/reservations",
        json={"user_id": "user-001"},
        headers={"Idempotency-Key": "request-001"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "activity_ended"


def test_replaying_same_idempotency_key_returns_original_success() -> None:
    endpoint = "/api/v1/activities/activity-001/reservations"
    headers = {"Idempotency-Key": "request-retry"}
    payload = {"user_id": "user-001"}

    first = client.post(endpoint, json=payload, headers=headers)
    retry = client.post(endpoint, json=payload, headers=headers)

    assert first.status_code == retry.status_code == 201
    assert first.json() == retry.json()
    assert client.get("/api/v1/activities/activity-001").json()["remaining_capacity"] == 1


def test_reusing_idempotency_key_for_another_user_is_rejected() -> None:
    endpoint = "/api/v1/activities/activity-001/reservations"
    headers = {"Idempotency-Key": "request-shared"}
    client.post(endpoint, json={"user_id": "user-001"}, headers=headers)

    response = client.post(endpoint, json={"user_id": "user-002"}, headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "idempotency_key_conflict"


def test_concurrent_requests_do_not_oversell_capacity() -> None:
    endpoint = "/api/v1/activities/activity-001/reservations"

    def submit(index: int) -> int:
        return client.post(
            endpoint,
            json={"user_id": f"user-{index}"},
            headers={"Idempotency-Key": f"request-{index}"},
        ).status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = list(executor.map(submit, range(8)))

    assert statuses.count(201) == 2
    assert statuses.count(409) == 6
    assert client.get("/api/v1/activities/activity-001").json()["remaining_capacity"] == 0
