"""报告导出：保存 Markdown 文件到 report/ 目录。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

DEFAULT_REPORT_DIR = Path("report")


def export_report(
    content: str,
    *,
    date: str | None = None,
    output_dir: Path | str | None = None,
) -> Path:
    """将报告内容写入 Markdown 文件。

    文件名格式：指数打分报告_YYYYMMDD.md
    同一天多次运行会覆盖已有文件。

    Args:
        content: Markdown 报告内容。
        date: 日期字符串 (YYYY-MM-DD)，None 则使用当前日期。
        output_dir: 输出目录，None 则使用 report/。

    Returns:
        写入的文件路径。
    """
    target_dir = Path(output_dir) if output_dir else DEFAULT_REPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    date_str = date or datetime.now().strftime("%Y-%m-%d")
    compact_date = date_str.replace("-", "")
    filename = f"指数打分报告_{compact_date}.md"

    filepath = target_dir / filename
    filepath.write_text(content, encoding="utf-8")
    return filepath
