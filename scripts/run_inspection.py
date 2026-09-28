"""调用本地巡检 API，并将结果保存为 JSON 与 Markdown。"""

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def render_markdown(report: dict[str, object]) -> str:
    """将巡检 JSON 转成便于阅读和归档的 Markdown 报告。"""
    checked_at = str(report.get("checked_at", "未知"))
    lines = [
        "# OpsPilot 巡检报告",
        "",
        f"- 巡检编号：`{report.get('inspection_id', '未知')}`",
        f"- 环境：{report.get('environment', '未知')}",
        f"- 总体状态：**{str(report.get('status', 'unknown')).upper()}**",
        f"- 检查时间：{checked_at}",
        "",
        "## 检查项",
        "",
    ]
    for check in report.get("checks", []):
        lines.extend([
            f"### {check.get('check_id', 'unknown')}：{str(check.get('status', 'unknown')).upper()}",
            f"- 严重级别：{check.get('severity', 'unknown')}",
            f"- 证据：{str(check.get('evidence', '')).replace(chr(10), ' ')}",
            f"- 建议：{str(check.get('recommendation', '')).replace(chr(10), ' ')}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def request_inspection(base_url: str, timeout: float) -> dict[str, object]:
    request = Request(
        f"{base_url.rstrip('/')}/api/v1/inspections/run",
        data=b"",
        method="POST",
        headers={"Accept": "application/json"},
    )
    with urlopen(request, timeout=timeout) as response:
        report = json.loads(response.read().decode("utf-8"))
    if not isinstance(report, dict) or not isinstance(report.get("checks"), list):
        raise ValueError("巡检接口返回的数据结构不符合预期")
    return report


def save_report(report: dict[str, object], output_dir: Path) -> tuple[Path, Path]:
    inspection_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(report.get("inspection_id", "inspection")))
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{inspection_id}.json"
    markdown_path = output_dir / f"{inspection_id}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description="执行 OpsPilot 巡检并保存 JSON/Markdown 报告")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="OpsPilot 服务根地址")
    parser.add_argument("--output", type=Path, default=Path("reports/generated"), help="报告输出目录")
    parser.add_argument("--timeout", type=float, default=15, help="接口超时秒数")
    args = parser.parse_args()

    try:
        report = request_inspection(args.url, args.timeout)
        json_path, markdown_path = save_report(report, args.output)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        print(f"巡检失败，未生成报告：{exc}", file=sys.stderr)
        return 1

    print(f"巡检状态：{str(report.get('status', 'unknown')).upper()}")
    print(f"JSON 报告：{json_path}")
    print(f"可读报告：{markdown_path}")
    return 2 if report.get("status") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
