"""AkShare 数据拉取器。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import akshare as ak  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]

from index_score.config.models import IndexInfo, IndexQuote, IndexValuation

logger = logging.getLogger(__name__)

US_SYMBOL_MAP: dict[str, str] = {
    "IXIC": ".IXIC",
    "SPX": ".INX",
    "DJI": ".DJI",
    "NDX": ".NDX",
}


class FetchError(Exception):
    """数据拉取失败。"""


def _resolve_a_share_symbol(code: str) -> str:
    if code.startswith("3") or code.startswith("1"):
        return f"sz{code}"
    return f"sh{code}"


def _resolve_us_symbol(code: str) -> str:
    return US_SYMBOL_MAP.get(code, f".{code}")


def _to_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result


def _to_str_date(value: Any) -> str:
    if isinstance(value, str):
        return value[:10]
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result == 0.0:
        return 0.0
    return result


def fetch_price_history(
    index_info: IndexInfo,
    years: int = 3,
) -> list[IndexQuote]:
    code = index_info.code
    market = index_info.market
    name = index_info.name
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y%m%d")

    try:
        if market == "US":
            df = _fetch_us_price_history(code)
        else:
            df = _fetch_a_share_price_history(code)
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"拉取行情数据失败: {code} ({name}), error={exc}") from exc

    if df is None or df.empty:
        raise FetchError(f"行情数据为空: {code} ({name})")

    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= pd.to_datetime(start_date)]

    if df.empty:
        raise FetchError(
            f"筛选后行情数据为空: {code} ({name}), start_date={start_date}"
        )

    return _map_quotes(df, code, name)


def _fetch_a_share_price_history(
    code: str,
) -> pd.DataFrame:
    symbol = _resolve_a_share_symbol(code)
    df = _try_fetch_a_share_tx(symbol)
    if df is not None and not df.empty:
        return df

    df = _try_fetch_a_share_sina(symbol)
    if df is not None and not df.empty:
        return df

    raise FetchError(
        f"所有A股行情数据源均失败: {code} "
        f"(尝试: 腾讯 stock_zh_index_daily_tx, 新浪 stock_zh_index_daily)"
    )


def _try_fetch_a_share_tx(symbol: str) -> pd.DataFrame | None:
    try:
        df = ak.stock_zh_index_daily_tx(symbol=symbol)
    except Exception as exc:
        logger.debug("腾讯行情拉取失败: %s, error=%s", symbol, exc)
        return None
    if df is None or df.empty:
        return None
    df = df.rename(columns={"amount": "volume"})
    df["date"] = pd.to_datetime(df["date"])
    return df


def _try_fetch_a_share_sina(symbol: str) -> pd.DataFrame | None:
    try:
        df = ak.stock_zh_index_daily(symbol=symbol)
    except Exception as exc:
        logger.debug("新浪行情拉取失败: %s, error=%s", symbol, exc)
        return None
    if df is None or df.empty:
        return None
    df["date"] = pd.to_datetime(df["date"])
    return df


def _fetch_us_price_history(
    code: str,
) -> pd.DataFrame:
    symbol = _resolve_us_symbol(code)
    df = ak.index_us_stock_sina(symbol=symbol)
    if df is None or df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"])
    return df


def _map_quotes(df: pd.DataFrame, code: str, name: str) -> list[IndexQuote]:
    required_cols = {"date", "open", "high", "low", "close", "volume"}
    missing = required_cols - set(df.columns)
    if missing:
        raise FetchError(f"行情数据缺少必要字段: {missing} (code={code})")

    quotes: list[IndexQuote] = []
    for row in df.itertuples(index=False):
        quotes.append(
            IndexQuote(
                code=code,
                name=name,
                date=_to_str_date(row.date),
                open=_to_float(row.open),
                close=_to_float(row.close),
                high=_to_float(row.high),
                low=_to_float(row.low),
                volume=_to_float(row.volume),
                adj_close=_to_float(row.close),
            )
        )
    return quotes


def fetch_quote(index_info: IndexInfo) -> IndexQuote:
    quotes = fetch_price_history(index_info, years=1)
    if not quotes:
        raise FetchError(f"行情数据为空: {index_info.code} ({index_info.name})")
    return quotes[-1]


def fetch_valuation(index_info: IndexInfo) -> IndexValuation:
    code = index_info.code
    market = index_info.market
    name = index_info.name

    if market != "CN":
        return IndexValuation(
            code=code,
            date=datetime.now().strftime("%Y-%m-%d"),
        )

    try:
        df = ak.stock_zh_index_value_csindex(symbol=code)
    except Exception as exc:
        raise FetchError(f"拉取估值数据失败: {code} ({name}), error={exc}") from exc

    if df is None or df.empty:
        raise FetchError(f"估值数据为空: {code} ({name})")

    row = df.iloc[0]
    pe_ttm = _to_optional_float(row.get("市盈率1"))
    dividend_yield = _to_optional_float(row.get("股息率1"))
    date = _to_str_date(row.get("日期", datetime.now()))

    return IndexValuation(
        code=code,
        date=date,
        pe_ttm=pe_ttm,
        dividend_yield=dividend_yield,
    )
