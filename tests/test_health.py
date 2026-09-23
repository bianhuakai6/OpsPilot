from fastapi.testclient import TestClient

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


def test_register_succeeds_and_reduces_capacity() -> None:
    response = client.post(
        "/api/v1/activities/activity-001/registrations",
        json={"user_id": "user-001"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "registered"
    assert client.get("/api/v1/activities/activity-001").json()["remaining_capacity"] == 1


def test_duplicate_registration_is_rejected() -> None:
    endpoint = "/api/v1/activities/activity-001/registrations"
    client.post(endpoint, json={"user_id": "user-001"})

    response = client.post(endpoint, json={"user_id": "user-001"})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "already_registered"


def test_capacity_exhaustion_is_rejected() -> None:
    endpoint = "/api/v1/activities/activity-001/registrations"
    client.post(endpoint, json={"user_id": "user-001"})
    client.post(endpoint, json={"user_id": "user-002"})

    response = client.post(endpoint, json={"user_id": "user-003"})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "capacity_exhausted"


def test_empty_user_id_is_rejected() -> None:
    response = client.post(
        "/api/v1/activities/activity-001/registrations",
        json={"user_id": ""},
    )

    assert response.status_code == 422


def test_registration_before_start_is_rejected() -> None:
    activities["activity-001"] = Activity(
        activity_id="activity-001",
        name="未来活动",
        starts_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        ends_at=datetime(2099, 1, 2, tzinfo=timezone.utc),
        capacity=1,
    )

    response = client.post(
        "/api/v1/activities/activity-001/registrations",
        json={"user_id": "user-001"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "activity_not_started"


def test_registration_after_end_is_rejected() -> None:
    activities["activity-001"] = Activity(
        activity_id="activity-001",
        name="已结束活动",
        starts_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        ends_at=datetime(2020, 1, 2, tzinfo=timezone.utc),
        capacity=1,
    )

    response = client.post(
        "/api/v1/activities/activity-001/registrations",
        json={"user_id": "user-001"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "activity_ended"
