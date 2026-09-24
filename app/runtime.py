from app.config import Settings
from app.database import create_database_engine
from app.redis_client import create_redis_client


# 应用运行时资源
settings = Settings.from_env()
database_engine = create_database_engine(settings) if settings.storage == "mysql" else None
redis_client = create_redis_client(settings.redis_url) if settings.redis_enabled else None
