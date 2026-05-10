"""因子打分：分位→连续分数插值 + 标签映射。"""

from __future__ import annotations

from index_score.config.models import ScoreRange

_LABEL_THRESHOLDS: list[tuple[float, str]] = [
    (2.0, "极便宜"),
    (4.0, "便宜"),
    (6.0, "中性"),
    (8.0, "偏贵"),
    (float("inf"), "极贵"),
]


def percentile_to_score(
    percentile: float,
    score_ranges: list[ScoreRange],
) -> float:
    """将百分位 (0~100) 转换为连续分数 (1.0~9.0)，保留 1 位小数。

    使用 score_ranges 定义的锚点做分段线性插值。
    起点 (0, first_score) 是隐含的。
    """
    if not score_ranges:
        return 5.0

    sorted_ranges = sorted(score_ranges, key=lambda r: r.max_percentile)

    control_points: list[tuple[float, float]] = [(0.0, sorted_ranges[0].score)]
    for sr in sorted_ranges:
        control_points.append((sr.max_percentile, sr.score))

    p = max(0.0, min(100.0, percentile))

    for i in range(len(control_points) - 1):
        x0, y0 = control_points[i]
        x1, y1 = control_points[i + 1]
        if p <= x1 or i == len(control_points) - 2:
            if x1 == x0:
                return _round_score(y0)
            ratio = (p - x0) / (x1 - x0)
            return _round_score(y0 + ratio * (y1 - y0))

    return _round_score(control_points[-1][1])


def score_to_label(score: float) -> str:
    """将连续分数映射为文字标签。"""
    for threshold, label in _LABEL_THRESHOLDS:
        if score <= threshold:
            return label
    return "极贵"


def _round_score(value: float) -> float:
    return round(max(1.0, min(9.0, value)), 1)
