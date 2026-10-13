from app import database
from app.config import Settings


def test_mysql_engine_uses_bounded_connection_timeouts(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_create_engine(url: str, **kwargs: object) -> object:
        captured["url"] = url
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(database, "create_engine", fake_create_engine)
    database.create_database_engine(Settings(storage="mysql"))

    assert captured["pool_pre_ping"] is True
    assert captured["connect_args"] == {"connect_timeout": 2, "read_timeout": 2, "write_timeout": 2}
