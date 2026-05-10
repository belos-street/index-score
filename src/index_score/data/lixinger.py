"""理杏仁 Open API 客户端。

接口文档: https://www.lixinger.com/open/api/doc?api-key=cn/index
核心接口: POST /api/cn/index/fundamental
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

from index_score.config.models import IndexInfo, IndexValuation, LixingerConfig
from index_score.data.exceptions import FetchError, LixingerAPIError

logger = logging.getLogger(__name__)

FUNDAMENTAL_METRICS: list[str] = [
    "pe_ttm.mcw",
    "pb.mcw",
    "dyr.mcw",
    "pe_ttm.y5.mcw.cvpos",
    "pb.y5.mcw.cvpos",
    "dyr.y5.mcw.cvpos",
]


class LixingerClient:
    """理杏仁 Open API 客户端。"""

    def __init__(self, config: LixingerConfig) -> None:
        self._token = config.token
        self._base_url = config.base_url.rstrip("/")
        self._timeout = config.timeout

        if not self._token:
            raise FetchError("理杏仁 Token 未配置，请在 .env 中设置 LIXINGER_TOKEN")

    def _post(self, path: str, body: dict[str, Any]) -> Any:
        url = f"{self._base_url}{path}"
        body["token"] = self._token
        try:
            resp = requests.post(url, json=body, timeout=self._timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise LixingerAPIError(f"理杏仁 API 请求失败: {exc}") from exc

        result = resp.json()
        if result.get("code") != 1:
            raise LixingerAPIError(
                f"理杏仁 API 业务错误: code={result.get('code')}, "
                f"message={result.get('message')}"
            )
        return result.get("data")

    def fetch_fundamental(
        self,
        stock_codes: list[str],
        date: str | None = None,
        metrics_list: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """拉取指数基本面数据。

        Args:
            stock_codes: 指数代码列表，长度 1~100。
            date: 指定日期，格式 YYYY-MM-DD，默认最新。
            metrics_list: 指标列表，默认使用 FUNDAMENTAL_METRICS。

        Returns:
            原始 API 返回的 data 数组。
        """
        body: dict[str, Any] = {
            "stockCodes": stock_codes,
            "metricsList": metrics_list or FUNDAMENTAL_METRICS,
        }
        if date:
            body["date"] = date

        data = self._post("/cn/index/fundamental", body)
        if not isinstance(data, list):
            raise LixingerAPIError(
                f"理杏仁 API 返回格式异常: 期望 list, 实际 {type(data)}"
            )
        return data


def fetch_valuation(
    client: LixingerClient,
    index_info: IndexInfo,
) -> IndexValuation:
    """通过理杏仁 API 拉取单指数估值数据。

    Args:
        client: 理杏仁 API 客户端。
        index_info: 指数信息。

    Returns:
        包含估值绝对值和分位点的 IndexValuation 实例。
    """
    code = index_info.lixinger_code or index_info.code
    today = datetime.now().strftime("%Y-%m-%d")

    data = client.fetch_fundamental([code], date=today)
    if not data:
        raise FetchError(f"理杏仁 API 未返回数据: {code} ({index_info.name})")

    item = data[0]
    date_str = item.get("date", today)
    if isinstance(date_str, str) and len(date_str) > 10:
        date_str = date_str[:10]

    return IndexValuation(
        code=index_info.code,
        date=date_str,
        pe_ttm=_to_optional_float(item.get("pe_ttm.mcw")),
        pe_percentile_5y=_to_percentile(item.get("pe_ttm.y5.mcw.cvpos")),
        pb_lf=_to_optional_float(item.get("pb.mcw")),
        pb_percentile_5y=_to_percentile(item.get("pb.y5.mcw.cvpos")),
        dividend_yield=_to_dividend_yield(item.get("dyr.mcw")),
        dividend_yield_percentile_5y=_to_percentile(item.get("dyr.y5.mcw.cvpos")),
    )


def _to_optional_float(value: Any) -> float | None:
    if value is None or value == "N/A":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def _to_percentile(value: Any) -> float | None:
    """将理杏仁 0~1 的分位值转换为 0~100 的百分位。"""
    if value is None or value == "N/A":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result * 100


def _to_dividend_yield(value: Any) -> float | None:
    """将理杏仁 0~1 的股息率转换为百分比。"""
    if value is None or value == "N/A":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result * 100
