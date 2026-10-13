"""结构化只读 Runbook：为告警提供可验证的诊断步骤和人工恢复建议。"""

from typing import Any


RUNBOOKS: tuple[dict[str, Any], ...] = (
    {
        "runbook_id": "redis-connectivity",
        "check_id": "redis_connectivity",
        "title": "Redis 连接异常排查",
        "symptoms": ["巡检报告中 redis_connectivity 为 fail", "/readyz 返回 redis_unavailable"],
        "safe_checks": [
            {"kind": "command", "value": "docker compose ps redis", "expected": "State 为 running，Health 为 healthy"},
            {"kind": "command", "value": "docker compose logs --tail 50 redis", "expected": "检查最近启动、退出或连接错误"},
            {"kind": "command", "value": "docker exec opspilot-redis redis-cli PING", "expected": "返回 PONG"},
            {"kind": "browser", "value": "http://127.0.0.1:8000/readyz", "expected": "status=ready 且 redis=connected"},
        ],
        "hypotheses": [
            "Redis 容器未运行或健康检查未通过",
            "API 与 Redis 的 Compose 网络连接异常",
            "Redis 正在重启或连接被拒绝",
        ],
        "manual_actions": [
            "确认容器状态与日志后，由操作者决定是否启动 Redis 服务",
            "恢复后重新运行巡检，确认 redis_connectivity 变为 pass",
        ],
        "forbidden_actions": ["不要执行 FLUSHALL/FLUSHDB", "不要删除 Redis 数据卷"],
        "requires_human_approval": True,
    },
    {
        "runbook_id": "mysql-connectivity",
        "check_id": "mysql_connectivity",
        "title": "MySQL 连接异常排查",
        "symptoms": ["巡检报告中 mysql_connectivity 为 fail", "/readyz 返回 database_unavailable"],
        "safe_checks": [
            {"kind": "command", "value": "docker compose ps mysql", "expected": "State 为 running，Health 为 healthy"},
            {"kind": "command", "value": "docker compose logs --tail 50 mysql", "expected": "检查启动、连接数或磁盘相关错误"},
            {"kind": "command", "value": "docker exec opspilot-mysql mysqladmin ping -h 127.0.0.1", "expected": "mysqld is alive"},
            {"kind": "browser", "value": "http://127.0.0.1:8000/readyz", "expected": "status=ready 且 mysql=connected"},
        ],
        "hypotheses": [
            "MySQL 容器不可用或仍在启动",
            "连接池无法建立新连接",
            "数据库资源、网络或凭据配置异常",
        ],
        "manual_actions": [
            "结合容器日志确认原因后，由操作者决定是否恢复 MySQL 服务",
            "恢复后重新运行巡检，确认 mysql_connectivity 变为 pass",
        ],
        "forbidden_actions": ["不要删除 MySQL 数据卷", "不要在未备份时执行数据修复语句"],
        "requires_human_approval": True,
    },
)


def list_runbooks() -> list[dict[str, Any]]:
    return [dict(item) for item in RUNBOOKS]


def get_runbook(runbook_id: str) -> dict[str, Any] | None:
    for runbook in RUNBOOKS:
        if runbook["runbook_id"] == runbook_id:
            return dict(runbook)
    return None


def get_runbook_for_check(check_id: str) -> dict[str, Any] | None:
    for runbook in RUNBOOKS:
        if runbook["check_id"] == check_id:
            return dict(runbook)
    return None
