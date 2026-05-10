"""打分表格组件。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import DataTable, Static

if TYPE_CHECKING:
    from index_score.config.models import IndexScore

COLUMNS = [
    ("指数名称", "auto"),
    ("代码", 10),
    ("模板", 10),
    ("总分", 8),
    ("估值水平", 10),
]

SCORE_COLOR_MAP: dict[str, str] = {
    "green": "green",
    "yellow": "yellow",
    "red": "red",
    "grey": "dim",
}


def score_color(score: IndexScore) -> str:
    s = score.total_score
    if s <= 0:
        return "grey"
    if s <= 3:
        return "green"
    if s <= 6:
        return "yellow"
    return "red"


class ScoreTable(Static):
    """封装 DataTable，提供指数打分表格展示。"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._sorted_scores: list[IndexScore] = []

    def compose(self):
        table = DataTable(cursor_type="row")
        table.focus()
        yield table

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for label, width in COLUMNS:
            if width == "auto":
                table.add_column(label, width=None)
            else:
                table.add_column(label, width=width)

    def show_loading(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        self._sorted_scores = []
        table.add_row("⏳ 正在加载数据...", "", "", "", "")

    def show_error(self, msg: str) -> None:
        table = self.query_one(DataTable)
        table.clear()
        self._sorted_scores = []
        table.add_row(f"❌ {msg}", "", "", "", "")

    def refresh_data(self, scores: list[IndexScore]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        if not scores:
            self.show_error("无可用打分数据")
            return
        self._sorted_scores = sorted(scores, key=lambda s: s.total_score)
        for s in self._sorted_scores:
            color_key = score_color(s)
            color_css = SCORE_COLOR_MAP.get(color_key, "")
            score_str = f"{s.total_score:.1f}" if s.total_score > 0 else "0.0"
            table.add_row(
                s.name,
                s.code,
                s.template,
                score_str,
                s.label,
                style=color_css,
            )

    def get_selected_score(self) -> IndexScore | None:
        if not self._sorted_scores:
            return None
        table = self.query_one(DataTable)
        if table.cursor_row is None:
            return None
        row = table.cursor_row
        if 0 <= row < len(self._sorted_scores):
            return self._sorted_scores[row]
        return None
