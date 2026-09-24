from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import Settings


def create_database_engine(settings: Settings) -> Engine:
    """创建数据库引擎；连接池参数集中在此，便于后续统一调整。"""
    return create_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=10)


def check_database(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one() == 1
