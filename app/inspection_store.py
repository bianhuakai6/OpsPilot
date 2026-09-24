import json

from sqlalchemy import text
from sqlalchemy.engine import Engine


def ensure_inspection_tables(engine: Engine) -> None:
    """启动时补齐巡检表，避免已有本地数据卷不会重复执行 init SQL。"""
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS inspection_runs (
                inspection_id VARCHAR(64) PRIMARY KEY,
                environment VARCHAR(32) NOT NULL,
                status VARCHAR(16) NOT NULL,
                checked_at DATETIME(6) NOT NULL,
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS inspection_checks (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                inspection_id VARCHAR(64) NOT NULL,
                check_id VARCHAR(64) NOT NULL,
                status VARCHAR(16) NOT NULL,
                severity VARCHAR(16) NOT NULL,
                evidence TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                CONSTRAINT fk_inspection_checks_run FOREIGN KEY (inspection_id) REFERENCES inspection_runs(inspection_id),
                INDEX idx_inspection_checks_run (inspection_id)
            )
        """))


def save_inspection(engine: Engine, report: dict[str, object]) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO inspection_runs (inspection_id, environment, status, checked_at) VALUES (:id, :environment, :status, :checked_at)"),
            {"id": report["inspection_id"], "environment": report["environment"], "status": report["status"], "checked_at": report["checked_at"]},
        )
        connection.execute(
            text("INSERT INTO inspection_checks (inspection_id, check_id, status, severity, evidence, recommendation) VALUES (:id, :check_id, :status, :severity, :evidence, :recommendation)"),
            [{"id": report["inspection_id"], **check} for check in report["checks"]],
        )


def load_inspection_history(engine: Engine, limit: int = 20) -> list[dict[str, object]]:
    with engine.connect() as connection:
        runs = connection.execute(
            text("SELECT inspection_id, environment, status, checked_at FROM inspection_runs ORDER BY checked_at DESC LIMIT :limit"),
            {"limit": limit},
        ).mappings().all()
        result = []
        for run in runs:
            checks = connection.execute(
                text("SELECT check_id, status, severity, evidence, recommendation FROM inspection_checks WHERE inspection_id = :id ORDER BY id"),
                {"id": run["inspection_id"]},
            ).mappings().all()
            result.append({**dict(run), "checks": [dict(check) for check in checks]})
        return result
