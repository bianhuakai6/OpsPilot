from app.config import Settings
from app.database import create_database_engine


# 应用运行时资源
settings = Settings.from_env()
database_engine = create_database_engine(settings) if settings.storage == "mysql" else None
