from collections import deque
from datetime import datetime, timezone
import ctypes
import os
import platform
import shutil

from app.database import check_database
from app.inspection_store import save_inspection
from app.metrics import metrics_freshness, metrics_payload
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


def _memory_snapshot() -> tuple[int, int] | None:
    """返回总内存和可用内存字节数；无法读取时由巡检标记为 skipped。"""
    if platform.system() == "Windows":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong),
                        ("total", ctypes.c_ulonglong), ("available", ctypes.c_ulonglong),
                        ("page_total", ctypes.c_ulonglong), ("page_available", ctypes.c_ulonglong),
                        ("virtual_total", ctypes.c_ulonglong), ("virtual_available", ctypes.c_ulonglong),
                        ("extended", ctypes.c_ulonglong)]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.total, status.available
        return None
    if hasattr(os, "sysconf"):
        page_size = os.sysconf("SC_PAGE_SIZE")
        total = page_size * os.sysconf("SC_PHYS_PAGES")
        available = page_size * os.sysconf("SC_AVPHYS_PAGES")
        return total, available
    return None


def _resource_checks() -> list[dict[str, str]]:
    """读取只读主机资源指标，低于 10% 可用空间时提示风险。"""
    checks: list[dict[str, str]] = []
    try:
        usage = shutil.disk_usage(os.path.abspath(os.sep))
        free_percent = usage.free / usage.total * 100 if usage.total else 0
        checks.append(_check(
            "disk_space",
            "pass" if free_percent >= 10 else "fail",
            "info" if free_percent >= 10 else "critical",
            f"系统盘可用空间 {free_percent:.1f}%（{usage.free // (1024 ** 3)} GiB）",
            "无需处理" if free_percent >= 10 else "清理磁盘或扩容文件系统",
        ))
    except OSError as exc:
        checks.append(_check("disk_space", "skipped", "warning", f"无法读取系统盘: {type(exc).__name__}", "检查运行账户和文件系统权限"))

    try:
        memory = _memory_snapshot()
        if memory is None:
            raise RuntimeError("memory_api_unavailable")
        total, available = memory
        available_percent = available / total * 100 if total else 0
        checks.append(_check(
            "memory_available",
            "pass" if available_percent >= 10 else "fail",
            "info" if available_percent >= 10 else "critical",
            f"可用内存 {available_percent:.1f}%（{available // (1024 ** 3)} GiB）",
            "无需处理" if available_percent >= 10 else "降低负载或增加内存",
        ))
    except (OSError, RuntimeError):
        checks.append(_check("memory_available", "skipped", "warning", "当前平台无法读取可用内存", "在支持的平台启用内存采集"))
    return checks


def run_inspection() -> dict[str, object]:
    """执行只读巡检；每项结果都包含证据和建议，不执行自动修复。"""
    checks: list[dict[str, str]] = [
        _check("process_liveness", "pass", "info", "应用进程能够响应巡检请求", "无需处理")
    ]

    # 配置检查先于依赖检查，帮助区分“依赖故障”和“配置本身不完整”。
    configuration_errors: list[str] = []
    if settings.storage not in {"memory", "mysql"}:
        configuration_errors.append("OPSPILOT_STORAGE 必须是 memory 或 mysql")
    if settings.storage == "mysql" and not settings.database_url.strip():
        configuration_errors.append("MySQL 模式缺少 OPSPILOT_DATABASE_URL")
    if settings.redis_enabled and not settings.redis_url.strip():
        configuration_errors.append("Redis 已启用但缺少 OPSPILOT_REDIS_URL")
    if not 1 <= settings.port <= 65535:
        configuration_errors.append("OPSPILOT_PORT 必须在 1 到 65535 之间")
    checks.append(_check(
        "configuration_integrity",
        "fail" if configuration_errors else "pass",
        "critical" if configuration_errors else "info",
        "; ".join(configuration_errors) if configuration_errors else "运行配置字段完整且值在允许范围内",
        "修正运行环境变量后重新巡检" if configuration_errors else "无需处理",
    ))

    metrics_text = metrics_payload().decode("utf-8", errors="replace")
    registry_available = "opspilot_http_requests_total" in metrics_text
    freshness_status, freshness_evidence = metrics_freshness()
    checks.append(_check(
        "metrics_registry",
        "pass" if registry_available else "fail",
        "info" if registry_available else "warning",
        "Prometheus 指标注册表可读取" if registry_available else "未发现 OpsPilot HTTP 指标",
        "无需处理" if registry_available else "检查指标初始化和 /metrics 路由",
    ))
    checks.append(_check(
        "metrics_freshness",
        freshness_status,
        "info" if freshness_status in {"pass", "skipped"} else "warning",
        freshness_evidence,
        "无需处理" if freshness_status == "pass" else "确认请求指标采集链路和 Prometheus 抓取状态",
    ))
    checks.extend(_resource_checks())

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
    if database_engine is not None:
        save_inspection(database_engine, report)
    inspection_history.appendleft(report)
    return report


def get_inspection_history() -> list[dict[str, object]]:
    return list(inspection_history)
