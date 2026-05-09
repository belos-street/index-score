"""数据清洗：标准化 fetcher 输出，处理缺失值和异常值。"""

from __future__ import annotations

import logging
import math

from index_score.config.models import IndexQuote, IndexValuation

logger = logging.getLogger(__name__)


def clean_quote(raw: IndexQuote) -> IndexQuote:
    """清洗行情数据。

    - OHLC 缺失时用收盘价填充
    - high < low 时互换
    - volume 为 NaN 时置 0
    """
    close = raw.close
    high = _safe_positive(raw.high, fallback=close)
    low = _safe_positive(raw.low, fallback=close)
    open_ = _safe_positive(raw.open, fallback=close)

    if high < low:
        high, low = low, high

    volume = raw.volume if not _is_nan(raw.volume) else 0.0

    return IndexQuote(
        code=raw.code,
        name=raw.name,
        date=raw.date,
        open=open_,
        close=close,
        high=high,
        low=low,
        volume=volume,
        adj_close=raw.adj_close if raw.adj_close > 0 else close,
    )


def clean_valuation(raw: IndexValuation) -> IndexValuation:
    """清洗估值数据。

    - 将 0.0 的估值字段转为 None（表示"无数据"），使打分模块可正确识别缺失
    - 负值 PE/PB 视为异常，也转 None
    - 负值股息率视为异常，转 None
    - 百分位字段：若对应绝对值为 None，百分位也置 None
    """
    pe = _to_optional_positive(raw.pe_ttm)
    pb = _to_optional_positive(raw.pb_lf)
    dividend_yield = _to_optional_non_negative(raw.dividend_yield)

    pe_pct = _to_optional(raw.pe_percentile_5y) if pe is not None else None
    pb_pct = _to_optional(raw.pb_percentile_5y) if pb is not None else None
    dy_pct = (
        _to_optional(raw.dividend_yield_percentile_5y)
        if dividend_yield is not None
        else None
    )

    return IndexValuation(
        code=raw.code,
        date=raw.date,
        pe_ttm=pe,
        pe_percentile_5y=pe_pct,
        pb_lf=pb,
        pb_percentile_5y=pb_pct,
        dividend_yield=dividend_yield,
        dividend_yield_percentile_5y=dy_pct,
    )


def _safe_positive(value: float, *, fallback: float) -> float:
    if _is_nan(value) or value <= 0:
        return fallback
    return value


def _is_nan(value: object) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _is_missing(value: object) -> bool:
    return value is None or _is_nan(value)


def _to_optional_positive(value: object) -> float | None:
    if _is_missing(value):
        return None
    assert isinstance(value, (int, float))
    if value <= 0:
        return None
    return float(value)


def _to_optional_non_negative(value: object) -> float | None:
    if _is_missing(value):
        return None
    assert isinstance(value, (int, float))
    if value < 0:
        return None
    return float(value)


def _to_optional(value: object) -> float | None:
    if _is_missing(value):
        return None
    assert isinstance(value, (int, float))
    return float(value)
