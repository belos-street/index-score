"""打分计算器：价格位置 + 模板加权求和。"""

from __future__ import annotations

from datetime import datetime, timedelta

from index_score.config.models import (
    FactorScore,
    IndexInfo,
    IndexQuote,
    IndexScore,
    IndexValuation,
    ScoreRange,
    ScoringConfig,
)
from index_score.scoring.factor import percentile_to_score, score_to_label  # noqa: I001


def calculate_price_position(
    quotes: list[IndexQuote],
    years: int,
) -> float | None:
    """计算价格在 N 年窗口内的位置百分位 (0~100)。

    quotes 需按日期升序排列。数据不足或窗口无波动时返回 None。
    """
    if not quotes:
        return None

    latest = quotes[-1]
    try:
        cutoff = (
            datetime.strptime(latest.date, "%Y-%m-%d") - timedelta(days=years * 365)
        ).strftime("%Y-%m-%d")
    except ValueError:
        return None

    window = [q for q in quotes if q.date >= cutoff]

    if len(window) < 2:
        return None

    values = [q.adj_close for q in window]
    low_val = min(values)
    high_val = max(values)

    if high_val == low_val:
        return None

    position = (latest.adj_close - low_val) / (high_val - low_val)
    return round(max(0.0, min(100.0, position * 100)), 2)


def calculate_index_score(
    index_info: IndexInfo,
    valuation: IndexValuation,
    price_position_percentile: float | None,
    scoring: ScoringConfig,
    score_ranges: list[ScoreRange],
) -> IndexScore:
    """根据模板因子加权求和计算指数综合分数。

    缺失因子的权重按比例重新分配给剩余因子。
    """
    template = scoring.templates[index_info.template]

    percentile_map = _build_percentile_map(valuation, price_position_percentile)

    available: list[FactorScore] = []
    missing_fields: list[str] = []

    for fc in template.factors:
        pct = percentile_map.get(fc.field)
        if pct is None:
            missing_fields.append(fc.field)
            continue

        score = percentile_to_score(pct, score_ranges)
        available.append(
            FactorScore(
                field=fc.field,
                label=score_to_label(score),
                percentile=round(pct, 2),
                score=score,
                weight=fc.weight,
                original_weight=fc.weight,
            )
        )

    if not available:
        return IndexScore(
            code=index_info.code,
            name=index_info.name,
            template=template.name,
            date=valuation.date,
            total_score=0.0,
            label="数据不足",
            factors=[],
            price_position_percentile=price_position_percentile,
            valuation=valuation,
        )

    total_orig_weight = sum(f.original_weight for f in available)
    total_score = 0.0

    for fs in available:
        fs.weight = round(fs.original_weight / total_orig_weight, 4)
        total_score += fs.score * fs.weight

    total_score = round(total_score, 1)

    return IndexScore(
        code=index_info.code,
        name=index_info.name,
        template=template.name,
        date=valuation.date,
        total_score=total_score,
        label=score_to_label(total_score),
        factors=available,
        price_position_percentile=price_position_percentile,
        valuation=valuation,
    )


def _build_percentile_map(
    valuation: IndexValuation,
    price_position_percentile: float | None,
) -> dict[str, float | None]:
    return {
        "pe_percentile_5y": valuation.pe_percentile_5y,
        "pb_percentile_5y": valuation.pb_percentile_5y,
        "dividend_yield_percentile_5y": valuation.dividend_yield_percentile_5y,
        "price_position_percentile_3y": price_position_percentile,
    }
