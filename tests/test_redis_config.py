from app.config import Settings


def test_redis_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("OPSPILOT_REDIS_ENABLED", raising=False)
    settings = Settings.from_env()
    assert settings.redis_enabled is False


def test_redis_can_be_enabled_by_environment(monkeypatch) -> None:
    monkeypatch.setenv("OPSPILOT_REDIS_ENABLED", "true")
    monkeypatch.setenv("OPSPILOT_REDIS_URL", "redis://localhost:6379/2")
    settings = Settings.from_env()
    assert settings.redis_enabled is True
    assert settings.redis_url.endswith("/2")
