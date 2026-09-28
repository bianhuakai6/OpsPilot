from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_page_is_available() -> None:
    response = TestClient(app).get("/dashboard")

    assert response.status_code == 200
    assert "OpsPilot 运维控制台" in response.text
    assert "重新巡检" in response.text
    assert "href=\"/load-test\"" in response.text


def test_load_test_page_is_available() -> None:
    response = TestClient(app).get("/load-test")

    assert response.status_code == 200
    assert "压力测试" in response.text
    assert 'id="chart"' in response.text
