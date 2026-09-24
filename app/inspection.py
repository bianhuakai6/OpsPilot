from collections import deque
from datetime import datetime, timezone

from app.database import check_database
from app.redis_client import check_redis
from app.runtime import database_engine, redis_client, settings


# 进程内保留最近巡检结果，后续可迁移到 MySQL。
inspection_history: deque[dict[str, object]] = deque(maxlen=20)


def _check(check_id: str, status: str, severity: str, evidence: str, recommendation: str) -> dict[str, str]:
    return {
        "check_id": check_id,
        "status": status,
        "severity": severity,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def run_inspection() -> dict[str, object]:
    """执行只读巡检；每项结果都包含证据和建议，不执行自动修复。"""
    checks: list[dict[str, str]] = [
        _check("process_liveness", "pass", "info", "应用进程能够响应巡检请求", "无需处理")
    ]

    if database_engine is None:
        checks.append(_check("mysql_connectivity", "skipped", "info", "当前 OPSPILOT_STORAGE 不是 mysql", "启用 MySQL 模式后再检查数据库"))
    else:
        try:
            available = check_database(database_engine)
            checks.append(_check("mysql_connectivity", "pass" if available else "fail", "info" if available else "critical", "SELECT 1 返回成功" if available else "数据库探测未返回成功", "保持数据库连接池可用" if available else "检查 MySQL 容器、连接串和凭据"))
        except Exception as exc:
            checks.append(_check("mysql_connectivity", "fail", "critical", f"数据库连接异常: {type(exc).__name__}", "检查 MySQL 容器、连接串和凭据"))

    if redis_client is None:
        checks.append(_check("redis_connectivity", "skipped", "info", "当前未启用 Redis", "启用 Redis 后再检查连接"))
    else:
        try:
            available = check_redis(redis_client)
            checks.append(_check("redis_connectivity", "pass" if available else "fail", "info" if available else "warning", "PING 返回 PONG" if available else "Redis 探测未成功", "保持 Redis 可用" if available else "检查 Redis 容器、URL 和端口"))
        except Exception as exc:
            checks.append(_check("redis_connectivity", "fail", "warning", f"Redis 连接异常: {type(exc).__name__}", "检查 Redis 容器、URL 和端口"))

    report = {
        "inspection_id": f"inspection-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}",
        "environment": settings.environment,
        "status": "fail" if any(item["status"] == "fail" for item in checks) else "pass",
        "checked_at": datetime.now(timezone.utc),
        "checks": checks,
    }
    inspection_history.appendleft(report)
    return report


def get_inspection_history() -> list[dict[str, object]]:
    return list(inspection_history)
