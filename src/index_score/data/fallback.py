"""兜底策略：带重试的数据拉取，失败时降级处理。"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from index_score.config.models import IndexInfo, IndexQuote, IndexValuation
from index_score.data.cleaner import clean_quote, clean_valuation
from index_score.data.exceptions import FetchError
from index_score.data.fetcher import fetch_price_history, fetch_valuation

if TYPE_CHECKING:
    from index_score.data.lixinger import LixingerClient

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 3

T = TypeVar("T")


@dataclass
class FetchResult:
    """拉取结果，包含原始数据和清洗后数据。"""

    quotes: list[IndexQuote]
    valuation: IndexValuation


def fetch_with_retry(
    fetch_fn: Callable[..., T],
    *args: object,
    **kwargs: object,
) -> T:
    """带重试的通用拉取。

    连续失败 MAX_RETRIES 次后抛出最后一次的异常。
    """
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fetch_fn(*args, **kwargs)
        except FetchError as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                logger.warning(
                    "拉取失败，第 %d/%d 次重试（%d 秒后）: %s",
                    attempt,
                    MAX_RETRIES,
                    RETRY_DELAY_SECONDS,
                    exc,
                )
                time.sleep(RETRY_DELAY_SECONDS)
    raise last_exc  # type: ignore[misc]


def fetch_all(
    index_info: IndexInfo,
    *,
    lixinger_client: LixingerClient | None = None,
    price_years: int = 3,
) -> FetchResult:
    """拉取指定指数的行情 + 估值数据，自动重试 + 清洗。

    流程：
    1. 拉取 price_years 年行情（重试 MAX_RETRIES 次）
    2. 通过理杏仁 API 拉取估值（重试 MAX_RETRIES 次，失败不阻断，返回空估值）
    3. 清洗行情和估值数据
    """
    raw_quotes = fetch_with_retry(fetch_price_history, index_info, years=price_years)
    quotes = [clean_quote(q) for q in raw_quotes]

    raw_valuation = _try_fetch_valuation(index_info, client=lixinger_client)
    valuation = clean_valuation(raw_valuation)

    return FetchResult(quotes=quotes, valuation=valuation)


def _try_fetch_valuation(
    index_info: IndexInfo,
    *,
    client: LixingerClient | None = None,
) -> IndexValuation:
    """拉取估值数据，重试 MAX_RETRIES 次。全部失败时返回空估值。"""
    try:
        return fetch_with_retry(fetch_valuation, index_info, client=client)
    except FetchError as exc:
        logger.warning(
            "估值数据拉取失败，跳过估值: %s (%s), error=%s",
            index_info.code,
            index_info.name,
            exc,
        )
        return IndexValuation(
            code=index_info.code,
            date="",
        )
