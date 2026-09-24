from dataclasses import dataclass
import os


# 运行配置边界
@dataclass(frozen=True)
class Settings:
    app_name: str = "OpsPilot"
    app_version: str = "0.1.0"
    environment: str = "local"
    host: str = "127.0.0.1"
    port: int = 8000
    storage: str = "memory"
    database_url: str = "mysql+pymysql://opspilot:opspilot_local_password@127.0.0.1:3306/opspilot?charset=utf8mb4"
    redis_enabled: bool = False
    redis_url: str = "redis://127.0.0.1:6379/0"

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量读取配置，未设置时使用本地开发默认值。"""
        port_text = os.getenv("OPSPILOT_PORT", str(cls.port))
        try:
            port = int(port_text)
        except ValueError as exc:
            raise ValueError("OPSPILOT_PORT 必须是整数") from exc

        return cls(
            app_name=os.getenv("OPSPILOT_APP_NAME", cls.app_name),
            app_version=os.getenv("OPSPILOT_APP_VERSION", cls.app_version),
            environment=os.getenv("OPSPILOT_ENV", cls.environment),
            host=os.getenv("OPSPILOT_HOST", cls.host),
            port=port,
            storage=os.getenv("OPSPILOT_STORAGE", cls.storage),
            database_url=os.getenv("OPSPILOT_DATABASE_URL", cls.database_url),
            redis_enabled=os.getenv("OPSPILOT_REDIS_ENABLED", "false").lower() in {"1", "true", "yes"},
            redis_url=os.getenv("OPSPILOT_REDIS_URL", cls.redis_url),
        )
