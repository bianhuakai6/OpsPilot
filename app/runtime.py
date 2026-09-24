from app.config import Settings
from app.database import create_database_engine
from app.inspection_store import ensure_inspection_tables
from app.redis_client import create_redis_client


# 应用运行时资源
settings = Settings.from_env()
database_engine = create_database_engine(settings) if settings.storage == "mysql" else None
if database_engine is not None:
    ensure_inspection_tables(database_engine)
redis_client = create_redis_client(settings.redis_url) if settings.redis_enabled else None
