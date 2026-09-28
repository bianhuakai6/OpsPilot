from pathlib import Path

from scripts.run_inspection import render_markdown, save_report


def test_render_markdown_includes_report_and_check_details() -> None:
    report = {
        "inspection_id": "inspection-test-001",
        "environment": "local",
        "status": "fail",
        "checked_at": "2026-09-28T01:02:03Z",
        "checks": [{
            "check_id": "mysql_connectivity",
            "status": "fail",
            "severity": "critical",
            "evidence": "连接失败\n连接超时",
            "recommendation": "检查 MySQL",
        }],
    }

    markdown = render_markdown(report)

    assert "OpsPilot 巡检报告" in markdown
    assert "**FAIL**" in markdown
    assert "mysql_connectivity：FAIL" in markdown
    assert "连接失败 连接超时" in markdown
    assert "检查 MySQL" in markdown


def test_save_report_writes_json_and_markdown(tmp_path: Path) -> None:
    report = {
        "inspection_id": "inspection-test-002",
        "environment": "local",
        "status": "pass",
        "checked_at": "2026-09-28T01:02:03Z",
        "checks": [],
    }

    json_path, markdown_path = save_report(report, tmp_path / "generated")

    assert json_path.exists()
    assert markdown_path.exists()
    assert '"status": "pass"' in json_path.read_text(encoding="utf-8")
    assert "OpsPilot 巡检报告" in markdown_path.read_text(encoding="utf-8")
