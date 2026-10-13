from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import Settings


def create_database_engine(settings: Settings) -> Engine:
    """创建数据库引擎；连接池和超时参数集中在此，避免依赖故障无限等待。"""
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"connect_timeout": 2, "read_timeout": 2, "write_timeout": 2},
    )


def check_database(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one() == 1
