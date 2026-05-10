"""报告生成器：组装打分结果 + LLM 解读为 Markdown 报告。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from index_score.report.template import REPORT_TEMPLATE

if TYPE_CHECKING:
    from index_score.config.models import IndexScore


@dataclass
class ReportSummary:
    """报告摘要数据。"""

    total_count: int
    avg_score_str: str
    cheapest_line: str
    most_expensive_line: str
    overall_level: str


@dataclass
class AnalysisItem:
    """单个指数的详细分析数据。"""

    code: str
    name: str
    title_line: str
    valuation_summary: str
    interpretation: str


FIELD_LABELS: dict[str, str] = {
    "pe_percentile_5y": "PE分位",
    "pb_percentile_5y": "PB分位",
    "dividend_yield_percentile_5y": "股息率分位",
    "price_position_percentile_3y": "价格位置",
}


def generate_report(
    scores: list[IndexScore],
    interpretations: dict[str, str],
    sort_by: str = "score",
    *,
    generated_at: str | None = None,
) -> str:
    """根据打分结果和 LLM 解读生成完整 Markdown 报告。

    Args:
        scores: 所有指数的打分结果。
        interpretations: 指数 code -> LLM 解读文本的映射。
        sort_by: 排序方式，"score" 按总分从低到高。
        generated_at: 报告生成时间，None 则使用当前时间。

    Returns:
        完整的 Markdown 报告字符串。
    """
    if not scores:
        return _empty_report(generated_at)

    sorted_scores = _sort_scores(scores, sort_by)
    summary = _build_summary(sorted_scores)
    score_table = _build_score_table(sorted_scores)
    analyses = _build_analyses(sorted_scores, interpretations)
    ts = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")

    return REPORT_TEMPLATE.render(
        generated_at=ts,
        summary=summary,
        score_table=score_table,
        analyses=analyses,
    )


def _sort_scores(
    scores: list[IndexScore],
    sort_by: str,
) -> list[IndexScore]:
    if sort_by == "score":
        return sorted(scores, key=lambda s: s.total_score)
    return sorted(scores, key=lambda s: s.code)


def _build_summary(scores: list[IndexScore]) -> ReportSummary:
    valid = [s for s in scores if s.total_score > 0]
    if not valid:
        return ReportSummary(
            total_count=len(scores),
            avg_score_str="N/A",
            cheapest_line="N/A",
            most_expensive_line="N/A",
            overall_level="数据不足",
        )

    total = sum(s.total_score for s in valid)
    avg = total / len(valid)
    cheapest = min(valid, key=lambda s: s.total_score)
    most_exp = max(valid, key=lambda s: s.total_score)

    return ReportSummary(
        total_count=len(scores),
        avg_score_str=f"{avg:.1f}",
        cheapest_line=_fmt_score_line(cheapest),
        most_expensive_line=_fmt_score_line(most_exp),
        overall_level=_overall_level(avg),
    )


def _fmt_score_line(score: IndexScore) -> str:
    return f"{score.name} ({score.total_score:.1f} 分)"


def _overall_level(avg: float) -> str:
    if avg <= 3.0:
        return "整体偏低，市场便宜"
    if avg <= 5.0:
        return "整体偏低"
    if avg <= 6.0:
        return "整体中性"
    if avg <= 7.5:
        return "整体偏高"
    return "整体偏高，市场偏贵"


def _build_score_table(scores: list[IndexScore]) -> str:
    all_fields = [
        "dividend_yield_percentile_5y",
        "pe_percentile_5y",
        "pb_percentile_5y",
        "price_position_percentile_3y",
    ]

    header = "| 排名 | 指数名称 | 模板 |"
    for field in all_fields:
        header += f" {FIELD_LABELS.get(field, field)} |"
    header += " 总分 | 估值水平 |"

    sep = "|------|---------|------|"
    for _ in all_fields:
        sep += "---|"
    sep += "------|---------|"

    rows = [header, sep]
    for rank, s in enumerate(scores, 1):
        factor_map = {f.field: f for f in s.factors}
        row = f"| {rank} | {s.name} | {s.template} |"
        for field in all_fields:
            ff = factor_map.get(field)
            if ff is not None:
                row += f" {ff.percentile:.1f}%({ff.score:.1f}) |"
            else:
                row += " - |"
        row += f" {s.total_score:.1f} | {s.label} |"
        rows.append(row)

    return "\n".join(rows)


def _build_analyses(
    scores: list[IndexScore],
    interpretations: dict[str, str],
) -> list[AnalysisItem]:
    items: list[AnalysisItem] = []
    for s in scores:
        interp = interpretations.get(s.code, "暂无 LLM 解读。")
        title = f"{s.name} ({s.code}) — {s.total_score:.1f} 分 · {s.label}"
        items.append(
            AnalysisItem(
                code=s.code,
                name=s.name,
                title_line=title,
                valuation_summary=_build_valuation_summary(s),
                interpretation=interp,
            )
        )
    return items


def _build_valuation_summary(score: IndexScore) -> str:
    parts: list[str] = []
    if score.valuation:
        v = score.valuation
        if v.pe_ttm is not None:
            parts.append(f"PE(TTM) {v.pe_ttm:.2f}")
        if v.pb_lf is not None:
            parts.append(f"PB {v.pb_lf:.2f}")
        if v.dividend_yield is not None:
            parts.append(f"股息率 {v.dividend_yield:.2%}")
    for f in score.factors:
        label = FIELD_LABELS.get(f.field, f.field)
        parts.append(f"{label} {f.percentile:.1f}%（分数 {f.score:.1f}）")
    if not parts:
        return "数据不足"
    return "；".join(parts)


def _empty_report(generated_at: str | None = None) -> str:
    ts = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        "# 大盘指数量化打分报告\n\n"
        f"> 生成日期：{ts} | 数据来源：理杏仁 API / AkShare\n\n"
        "暂无打分数据。\n"
    )
