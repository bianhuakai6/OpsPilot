from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_load_test_requests_are_counted_without_per_request_log() -> None:
    with patch("app.middleware.logging.getLogger") as get_logger:
        logger = get_logger.return_value
        response = TestClient(app).get("/healthz", headers={"X-OpsPilot-Load-Test": "true"})

    assert response.status_code == 200
    logger.info.assert_not_called()


def test_normal_requests_keep_structured_request_log() -> None:
    with patch("app.middleware.logging.getLogger") as get_logger:
        logger = get_logger.return_value
        response = TestClient(app).get("/healthz")

    assert response.status_code == 200
    logger.info.assert_called_once()
    assert logger.info.call_args.args == ("http_request",)
