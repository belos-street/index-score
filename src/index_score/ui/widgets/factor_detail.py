"""因子详情 ModalScreen。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

if TYPE_CHECKING:
    from index_score.config.models import IndexScore

VALUATION_FIELDS: list[tuple[str, str, bool]] = [
    ("pe_ttm", "PE(TTM)", False),
    ("pb_lf", "PB", False),
    ("dividend_yield", "股息率", True),
]

_PERCENTILE_MAP: dict[str, str] = {
    "pe_ttm": "pe_percentile_5y",
    "pb_lf": "pb_percentile_5y",
    "dividend_yield": "dividend_yield_percentile_5y",
}


def _fmt_val(v: float | None, pct: bool = False) -> str:
    if v is None:
        return "-"
    if pct:
        return f"{v:.2%}"
    return f"{v:.2f}"


def build_detail_content(score: IndexScore, interpretation: str) -> str:
    """构建详情 Modal 的纯文本内容。"""
    lines: list[str] = []

    title = (
        f"## {score.name} ({score.code})"
        f" — {score.total_score:.1f} 分 · {score.label}"
    )
    lines.append(title)
    lines.append("")

    lines.append("### 估值概况")
    lines.append("")

    if score.total_score <= 0:
        lines.append("数据不足，无法计算估值指标。")
    else:
        lines.append(
            f"{'指标':<12} {'当前值':>8} {'5年分位':>8} {'分数':>6} {'权重':>6}"
        )
        lines.append("-" * 46)

        if score.valuation:
            v = score.valuation
            for attr, label, is_pct in VALUATION_FIELDS:
                raw = getattr(v, attr, None)
                val_str = _fmt_val(raw, is_pct)

                pct_field = _PERCENTILE_MAP.get(attr, "")
                pct_val = (
                    getattr(v, pct_field, None) if pct_field else None
                )
                pct_str = (
                    f"{pct_val:.1f}%" if pct_val is not None else "-"
                )

                factor_score = "-"
                factor_weight = "-"
                for f in score.factors:
                    if f.field == pct_field:
                        factor_score = f"{f.score:.1f}"
                        factor_weight = f"{f.weight:.0%}"
                        break

                lines.append(
                    f"{label:<12} {val_str:>8} {pct_str:>8}"
                    f" {factor_score:>6} {factor_weight:>6}"
                )

        if score.price_position_percentile is not None:
            pp_score = "-"
            pp_weight = "-"
            for f in score.factors:
                if f.field == "price_position_percentile_3y":
                    pp_score = f"{f.score:.1f}"
                    pp_weight = f"{f.weight:.0%}"
                    break
            lines.append(
                f"{'价格位置':<12} {'-':>8}"
                f" {score.price_position_percentile:.1f}%"
                f" {pp_score:>6} {pp_weight:>6}"
            )

    lines.append("")
    lines.append("### LLM 解读")
    lines.append("")

    if interpretation.strip():
        lines.append(interpretation)
    else:
        lines.append("暂无 LLM 解读。")

    return "\n".join(lines)


class FactorDetailScreen(ModalScreen[None]):
    """因子详情 + LLM 解读的 ModalScreen。"""

    DEFAULT_CLASSES = "factor-detail-screen"
    BINDINGS = [Binding("escape", "dismiss", "关闭")]

    def __init__(
        self, score: IndexScore, interpretation: str
    ) -> None:
        super().__init__()
        self._score = score
        self._interpretation = interpretation

    def compose(self) -> ComposeResult:
        content = build_detail_content(
            self._score, self._interpretation
        )
        with VerticalScroll():
            yield Static(content, markup=False)
        yield Static("[Esc] 关闭", classes="footer-hint")

    def action_dismiss(self) -> None:
        self.dismiss()
