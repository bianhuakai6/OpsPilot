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
        )
