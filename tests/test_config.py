import pytest

from app.config import Settings


def test_settings_use_local_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "OPSPILOT_APP_NAME",
        "OPSPILOT_APP_VERSION",
        "OPSPILOT_ENV",
        "OPSPILOT_HOST",
        "OPSPILOT_PORT",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings.from_env()

    assert settings.app_name == "OpsPilot"
    assert settings.environment == "local"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_settings_read_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ENV", "test")
    monkeypatch.setenv("OPSPILOT_HOST", "0.0.0.0")
    monkeypatch.setenv("OPSPILOT_PORT", "9000")

    settings = Settings.from_env()

    assert settings.environment == "test"
    assert settings.host == "0.0.0.0"
    assert settings.port == 9000


def test_settings_reject_invalid_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_PORT", "not-a-number")

    with pytest.raises(ValueError, match="OPSPILOT_PORT"):
        Settings.from_env()
