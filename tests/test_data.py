"""数据拉取、清洗、兜底模块测试。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd  # type: ignore[import-untyped]
import pytest

from index_score.config.models import (
    IndexInfo,
    IndexQuote,
    IndexValuation,
    LixingerConfig,
)
from index_score.data.cleaner import clean_quote, clean_valuation
from index_score.data.exceptions import FetchError
from index_score.data.fallback import FetchResult, fetch_all, fetch_with_retry
from index_score.data.fetcher import (
    _map_quotes,
    _resolve_a_share_symbol,
    _resolve_us_symbol,
    _to_float,
    _to_str_date,
    fetch_price_history,
    fetch_quote,
    fetch_valuation,
)
from index_score.data.lixinger import (
    FUNDAMENTAL_METRICS,
    LixingerClient,
    _to_dividend_yield,
    _to_optional_float,
    _to_percentile,
)
from index_score.data.lixinger import (
    fetch_valuation as lixinger_fetch_valuation,
)


def _cn_index() -> IndexInfo:
    return IndexInfo(code="000922", name="中证红利", market="CN", template="dividend")


def _cn_index_with_li_code() -> IndexInfo:
    return IndexInfo(
        code="000922",
        name="中证红利",
        market="CN",
        template="dividend",
        lixinger_code="000922",
    )


def _us_index() -> IndexInfo:
    return IndexInfo(code="IXIC", name="纳指", market="US", template="growth")


def _lixinger_config() -> LixingerConfig:
    return LixingerConfig(
        token_env="LIXINGER_TOKEN",
        base_url="https://open.lixinger.com/api",
        timeout=30,
    )


def _sample_a_share_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2026-05-06", "2026-05-07", "2026-05-08"],
            "open": [4000.0, 4010.0, 4020.0],
            "high": [4050.0, 4060.0, 4070.0],
            "low": [3990.0, 4000.0, 4010.0],
            "close": [4030.0, 4040.0, 4050.0],
            "volume": [100000000, 110000000, 120000000],
        }
    )


def _sample_us_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2026-05-06", "2026-05-07", "2026-05-08"],
            "open": [25000.0, 25100.0, 25200.0],
            "high": [25500.0, 25600.0, 25700.0],
            "low": [24900.0, 25000.0, 25100.0],
            "close": [25400.0, 25500.0, 25600.0],
            "volume": [5000000000, 5100000000, 5200000000],
            "amount": [0, 0, 0],
        }
    )


def _sample_lixinger_fundamental_response() -> list[dict[str, Any]]:
    return [
        {
            "date": "2026-05-08T00:00:00.000Z",
            "pe_ttm.mcw": 12.5,
            "pb.mcw": 1.3,
            "dyr.mcw": 0.045,
            "pe_ttm.y5.mcw.cvpos": 0.35,
            "pb.y5.mcw.cvpos": 0.42,
            "dyr.y5.mcw.cvpos": 0.28,
        }
    ]


class TestSymbolMapping:
    def test_a_share_sh_prefix(self) -> None:
        assert _resolve_a_share_symbol("000922") == "sh000922"
        assert _resolve_a_share_symbol("930955") == "sh930955"
        assert _resolve_a_share_symbol("000300") == "sh000300"

    def test_a_share_sz_prefix(self) -> None:
        assert _resolve_a_share_symbol("399371") == "sz399371"
        assert _resolve_a_share_symbol("399006") == "sz399006"

    def test_etf_sz_prefix(self) -> None:
        assert _resolve_a_share_symbol("159201") == "sz159201"

    def test_etf_sh_prefix(self) -> None:
        assert _resolve_a_share_symbol("515450") == "sh515450"

    def test_us_symbol_mapping(self) -> None:
        assert _resolve_us_symbol("IXIC") == ".IXIC"
        assert _resolve_us_symbol("SPX") == ".INX"
        assert _resolve_us_symbol("DJI") == ".DJI"

    def test_us_symbol_fallback(self) -> None:
        assert _resolve_us_symbol("NDX") == ".NDX"
        assert _resolve_us_symbol("RUT") == ".RUT"


class TestHelperFunctions:
    def test_to_float_normal(self) -> None:
        assert _to_float(3.14) == pytest.approx(3.14)
        assert _to_float("2.5") == pytest.approx(2.5)
        assert _to_float(100) == pytest.approx(100.0)

    def test_to_float_invalid(self) -> None:
        assert _to_float(None) == 0.0
        assert _to_float("abc") == 0.0
        assert _to_float(float("nan")) != _to_float(float("nan"))

    def test_to_str_date_string(self) -> None:
        assert _to_str_date("2026-05-08") == "2026-05-08"
        assert _to_str_date("2026-05-08 12:00:00") == "2026-05-08"

    def test_to_str_date_datetime(self) -> None:
        dt = datetime(2026, 5, 8)
        assert _to_str_date(dt) == "2026-05-08"


class TestMapQuotes:
    def test_valid_dataframe(self) -> None:
        df = _sample_a_share_df()
        quotes = _map_quotes(df, "000922", "中证红利")

        assert len(quotes) == 3
        assert isinstance(quotes[0], IndexQuote)
        assert quotes[0].code == "000922"
        assert quotes[0].name == "中证红利"
        assert quotes[0].date == "2026-05-06"
        assert quotes[0].open == pytest.approx(4000.0)
        assert quotes[0].close == pytest.approx(4030.0)
        assert quotes[0].adj_close == pytest.approx(4030.0)

    def test_missing_columns_raises(self) -> None:
        df = pd.DataFrame({"date": ["2026-05-08"], "open": [100.0]})
        with pytest.raises(FetchError, match="缺少必要字段"):
            _map_quotes(df, "000922", "test")

    def test_last_quote_is_latest(self) -> None:
        df = _sample_a_share_df()
        quotes = _map_quotes(df, "000922", "中证红利")
        assert quotes[-1].date == "2026-05-08"


class TestFetchPriceHistory:
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_a_share_success_via_tx(
        self,
        mock_tx: Any,
        mock_sina: Any,
    ) -> None:
        mock_tx.return_value = pd.DataFrame(
            {
                "date": ["2026-05-06", "2026-05-07", "2026-05-08"],
                "open": [4000.0, 4010.0, 4020.0],
                "close": [4030.0, 4040.0, 4050.0],
                "high": [4050.0, 4060.0, 4070.0],
                "low": [3990.0, 4000.0, 4010.0],
                "amount": [100000000.0, 110000000.0, 120000000.0],
            }
        )
        quotes = fetch_price_history(_cn_index(), years=3)

        assert len(quotes) == 3
        mock_tx.assert_called_once_with(symbol="sh000922")
        mock_sina.assert_not_called()

    @patch("index_score.data.fetcher.ak.stock_zh_index_daily")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_a_share_fallback_to_sina(
        self,
        mock_tx: Any,
        mock_sina: Any,
    ) -> None:
        mock_tx.side_effect = ConnectionError("timeout")
        mock_sina.return_value = _sample_a_share_df()
        quotes = fetch_price_history(_cn_index(), years=3)

        assert len(quotes) == 3
        mock_tx.assert_called_once()
        mock_sina.assert_called_once_with(symbol="sh000922")

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    def test_us_success(self, mock_us: Any) -> None:
        mock_us.return_value = _sample_us_df()
        quotes = fetch_price_history(_us_index(), years=3)

        assert len(quotes) == 3
        mock_us.assert_called_once_with(symbol=".IXIC")

    @patch("index_score.data.fetcher.ak.stock_zh_index_daily")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_all_sources_empty_raises(
        self,
        mock_tx: Any,
        mock_sina: Any,
    ) -> None:
        mock_tx.return_value = pd.DataFrame()
        mock_sina.return_value = pd.DataFrame()
        with pytest.raises(FetchError, match="所有A股行情数据源均失败"):
            fetch_price_history(_cn_index())

    @patch("index_score.data.fetcher.ak.stock_zh_index_daily")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_all_sources_network_error_raises(
        self,
        mock_tx: Any,
        mock_sina: Any,
    ) -> None:
        mock_tx.side_effect = ConnectionError("timeout")
        mock_sina.side_effect = ConnectionError("timeout")
        with pytest.raises(FetchError, match="所有A股行情数据源均失败"):
            fetch_price_history(_cn_index())


class TestFetchQuote:
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_returns_latest_quote(self, mock_tx: Any, mock_sina: Any) -> None:
        mock_tx.return_value = pd.DataFrame(
            {
                "date": ["2026-05-06", "2026-05-07", "2026-05-08"],
                "open": [4000.0, 4010.0, 4020.0],
                "close": [4030.0, 4040.0, 4050.0],
                "high": [4050.0, 4060.0, 4070.0],
                "low": [3990.0, 4000.0, 4010.0],
                "amount": [100000000.0, 110000000.0, 120000000.0],
            }
        )
        quote = fetch_quote(_cn_index())

        assert isinstance(quote, IndexQuote)
        assert quote.date == "2026-05-08"
        assert quote.close == pytest.approx(4050.0)

    @patch("index_score.data.fetcher.ak.stock_zh_index_daily")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_empty_data_raises(self, mock_tx: Any, mock_sina: Any) -> None:
        mock_tx.return_value = pd.DataFrame()
        mock_sina.return_value = pd.DataFrame()
        with pytest.raises(FetchError):
            fetch_quote(_cn_index())


class TestLixingerHelpers:
    def test_to_optional_float_normal(self) -> None:
        assert _to_optional_float(3.14) == pytest.approx(3.14)
        assert _to_optional_float(0) == pytest.approx(0.0)
        assert _to_optional_float("2.5") == pytest.approx(2.5)

    def test_to_optional_float_none_and_na(self) -> None:
        assert _to_optional_float(None) is None
        assert _to_optional_float("N/A") is None

    def test_to_optional_float_invalid(self) -> None:
        assert _to_optional_float("abc") is None

    def test_to_percentile_converts_to_100_scale(self) -> None:
        assert _to_percentile(0.35) == pytest.approx(35.0)
        assert _to_percentile(0.0) == pytest.approx(0.0)
        assert _to_percentile(1.0) == pytest.approx(100.0)

    def test_to_percentile_none_and_na(self) -> None:
        assert _to_percentile(None) is None
        assert _to_percentile("N/A") is None

    def test_to_dividend_yield_converts_to_percent(self) -> None:
        assert _to_dividend_yield(0.045) == pytest.approx(4.5)
        assert _to_dividend_yield(0.0) == pytest.approx(0.0)

    def test_to_dividend_yield_none_and_na(self) -> None:
        assert _to_dividend_yield(None) is None
        assert _to_dividend_yield("N/A") is None


class TestLixingerClient:
    @patch.dict("os.environ", {"LIXINGER_TOKEN": "test-token"})
    def test_init_with_env_token(self) -> None:
        config = LixingerConfig(
            token_env="LIXINGER_TOKEN",
            base_url="https://open.lixinger.com/api",
            timeout=30,
        )
        client = LixingerClient(config)
        assert client._token == "test-token"

    def test_init_without_token_raises(self) -> None:
        config = LixingerConfig(
            token_env="NONEXISTENT_TOKEN",
            base_url="https://open.lixinger.com/api",
            timeout=30,
        )
        with pytest.raises(FetchError, match="理杏仁 Token 未配置"):
            LixingerClient(config)

    @patch("index_score.data.lixinger.requests.post")
    @patch.dict("os.environ", {"LIXINGER_TOKEN": "test-token"})
    def test_fetch_fundamental_success(self, mock_post: Any) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "code": 1,
            "data": _sample_lixinger_fundamental_response(),
            "message": "success",
        }
        mock_post.return_value = mock_resp

        config = LixingerConfig(
            token_env="LIXINGER_TOKEN",
            base_url="https://open.lixinger.com/api",
            timeout=30,
        )
        client = LixingerClient(config)
        data = client.fetch_fundamental(["000922"])

        assert len(data) == 1
        assert data[0]["pe_ttm.mcw"] == pytest.approx(12.5)
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"]["token"] == "test-token"
        assert call_kwargs.kwargs["json"]["stockCodes"] == ["000922"]
        assert call_kwargs.kwargs["json"]["metricsList"] == FUNDAMENTAL_METRICS

    @patch("index_score.data.lixinger.requests.post")
    @patch.dict("os.environ", {"LIXINGER_TOKEN": "test-token"})
    def test_fetch_fundamental_custom_metrics(self, mock_post: Any) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"code": 1, "data": [], "message": "success"}
        mock_post.return_value = mock_resp

        config = LixingerConfig(
            token_env="LIXINGER_TOKEN",
            base_url="https://open.lixinger.com/api",
            timeout=30,
        )
        client = LixingerClient(config)
        client.fetch_fundamental(["000922"], metrics_list=["pe_ttm.mcw"])

        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"]["metricsList"] == ["pe_ttm.mcw"]

    @patch("index_score.data.lixinger.requests.post")
    @patch.dict("os.environ", {"LIXINGER_TOKEN": "test-token"})
    def test_fetch_fundamental_api_error(self, mock_post: Any) -> None:
        from index_score.data.exceptions import LixingerAPIError

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "code": -1,
            "data": None,
            "message": "invalid token",
        }
        mock_post.return_value = mock_resp

        config = LixingerConfig(
            token_env="LIXINGER_TOKEN",
            base_url="https://open.lixinger.com/api",
            timeout=30,
        )
        client = LixingerClient(config)
        with pytest.raises(LixingerAPIError, match="业务错误"):
            client.fetch_fundamental(["000922"])

    @patch("index_score.data.lixinger.requests.post")
    @patch.dict("os.environ", {"LIXINGER_TOKEN": "test-token"})
    def test_fetch_fundamental_network_error(self, mock_post: Any) -> None:
        import requests as req_lib

        from index_score.data.exceptions import LixingerAPIError

        mock_post.side_effect = req_lib.ConnectionError("timeout")

        config = LixingerConfig(
            token_env="LIXINGER_TOKEN",
            base_url="https://open.lixinger.com/api",
            timeout=30,
        )
        client = LixingerClient(config)
        with pytest.raises(LixingerAPIError, match="请求失败"):
            client.fetch_fundamental(["000922"])


class TestFetchValuation:
    def test_valuation_success(self) -> None:
        mock_client = MagicMock(spec=LixingerClient)
        mock_client.fetch_fundamental.return_value = (
            _sample_lixinger_fundamental_response()
        )

        val = lixinger_fetch_valuation(mock_client, _cn_index())

        assert isinstance(val, IndexValuation)
        assert val.code == "000922"
        assert val.date == "2026-05-08"
        assert val.pe_ttm == pytest.approx(12.5)
        assert val.pe_percentile_5y == pytest.approx(35.0)
        assert val.pb_lf == pytest.approx(1.3)
        assert val.pb_percentile_5y == pytest.approx(42.0)
        assert val.dividend_yield == pytest.approx(4.5)
        assert val.dividend_yield_percentile_5y == pytest.approx(28.0)

    def test_valuation_uses_lixinger_code(self) -> None:
        mock_client = MagicMock(spec=LixingerClient)
        mock_client.fetch_fundamental.return_value = (
            _sample_lixinger_fundamental_response()
        )

        index = IndexInfo(
            code="000922",
            name="中证红利",
            market="CN",
            template="dividend",
            lixinger_code="000922",
        )
        lixinger_fetch_valuation(mock_client, index)

        call_args = mock_client.fetch_fundamental.call_args
        assert call_args[0][0] == ["000922"]

    def test_valuation_falls_back_to_code(self) -> None:
        mock_client = MagicMock(spec=LixingerClient)
        mock_client.fetch_fundamental.return_value = (
            _sample_lixinger_fundamental_response()
        )

        index = IndexInfo(
            code="000922",
            name="中证红利",
            market="CN",
            template="dividend",
        )
        lixinger_fetch_valuation(mock_client, index)

        call_args = mock_client.fetch_fundamental.call_args
        assert call_args[0][0] == ["000922"]

    def test_valuation_empty_data_raises(self) -> None:
        mock_client = MagicMock(spec=LixingerClient)
        mock_client.fetch_fundamental.return_value = []

        with pytest.raises(FetchError, match="未返回数据"):
            lixinger_fetch_valuation(mock_client, _cn_index())

    def test_valuation_partial_none_fields(self) -> None:
        mock_client = MagicMock(spec=LixingerClient)
        mock_client.fetch_fundamental.return_value = [
            {
                "date": "2026-05-08T00:00:00.000Z",
                "pe_ttm.mcw": 12.5,
                "pb.mcw": None,
                "dyr.mcw": None,
                "pe_ttm.y5.mcw.cvpos": 0.35,
                "pb.y5.mcw.cvpos": None,
                "dyr.y5.mcw.cvpos": None,
            }
        ]

        val = lixinger_fetch_valuation(mock_client, _cn_index())

        assert val.pe_ttm == pytest.approx(12.5)
        assert val.pe_percentile_5y == pytest.approx(35.0)
        assert val.pb_lf is None
        assert val.pb_percentile_5y is None
        assert val.dividend_yield is None
        assert val.dividend_yield_percentile_5y is None


class TestFetchValuationWithConfig:
    def test_fetch_valuation_without_client_uses_config(
        self,
    ) -> None:
        mock_lixinger_client = MagicMock(spec=LixingerClient)
        mock_lixinger_client.fetch_fundamental.return_value = (
            _sample_lixinger_fundamental_response()
        )

        mock_cfg = MagicMock()
        mock_cfg.lixinger = _lixinger_config()

        with (
            patch(
                "index_score.config.loader.load_config",
                return_value=mock_cfg,
            ),
            patch(
                "index_score.data.lixinger.LixingerClient",
                return_value=mock_lixinger_client,
            ),
        ):
            val = fetch_valuation(_cn_index())

        assert isinstance(val, IndexValuation)
        assert val.code == "000922"
        assert val.pe_ttm == pytest.approx(12.5)

    def test_fetch_valuation_no_config_raises(self) -> None:
        mock_cfg = MagicMock()
        mock_cfg.lixinger = None

        with (
            patch(
                "index_score.config.loader.load_config",
                return_value=mock_cfg,
            ),
            pytest.raises(FetchError, match="无法创建理杏仁客户端"),
        ):
            fetch_valuation(_cn_index())


class TestCleanQuote:
    def test_normal_quote_passthrough(self) -> None:
        raw = IndexQuote(
            code="000922",
            name="中证红利",
            date="2026-05-08",
            open=4000.0,
            close=4050.0,
            high=4060.0,
            low=3990.0,
            volume=100000000.0,
            adj_close=4050.0,
        )
        cleaned = clean_quote(raw)
        assert cleaned.open == pytest.approx(4000.0)
        assert cleaned.close == pytest.approx(4050.0)
        assert cleaned.high == pytest.approx(4060.0)
        assert cleaned.low == pytest.approx(3990.0)

    def test_zero_ohlc_uses_close_fallback(self) -> None:
        raw = IndexQuote(
            code="000922",
            name="中证红利",
            date="2026-05-08",
            open=0.0,
            close=100.0,
            high=0.0,
            low=0.0,
            volume=100000.0,
            adj_close=100.0,
        )
        cleaned = clean_quote(raw)
        assert cleaned.open == pytest.approx(100.0)
        assert cleaned.high == pytest.approx(100.0)
        assert cleaned.low == pytest.approx(100.0)

    def test_high_low_swapped(self) -> None:
        raw = IndexQuote(
            code="000922",
            name="中证红利",
            date="2026-05-08",
            open=100.0,
            close=100.0,
            high=90.0,
            low=110.0,
            volume=100000.0,
            adj_close=100.0,
        )
        cleaned = clean_quote(raw)
        assert cleaned.high == pytest.approx(110.0)
        assert cleaned.low == pytest.approx(90.0)

    def test_nan_volume_becomes_zero(self) -> None:
        raw = IndexQuote(
            code="000922",
            name="中证红利",
            date="2026-05-08",
            open=100.0,
            close=100.0,
            high=100.0,
            low=100.0,
            volume=float("nan"),
            adj_close=100.0,
        )
        cleaned = clean_quote(raw)
        assert cleaned.volume == pytest.approx(0.0)

    def test_zero_adj_close_uses_close(self) -> None:
        raw = IndexQuote(
            code="000922",
            name="中证红利",
            date="2026-05-08",
            open=100.0,
            close=100.0,
            high=100.0,
            low=100.0,
            volume=100000.0,
            adj_close=0.0,
        )
        cleaned = clean_quote(raw)
        assert cleaned.adj_close == pytest.approx(100.0)


class TestCleanValuation:
    def test_normal_valuation_passthrough(self) -> None:
        raw = IndexValuation(
            code="000922",
            date="2026-05-08",
            pe_ttm=8.5,
            pe_percentile_5y=30.0,
            pb_lf=1.2,
            pb_percentile_5y=45.0,
            dividend_yield=4.5,
            dividend_yield_percentile_5y=20.0,
        )
        cleaned = clean_valuation(raw)
        assert cleaned.pe_ttm == pytest.approx(8.5)
        assert cleaned.pb_lf == pytest.approx(1.2)
        assert cleaned.dividend_yield == pytest.approx(4.5)
        assert cleaned.pe_percentile_5y == pytest.approx(30.0)

    def test_zero_values_become_none(self) -> None:
        raw = IndexValuation(
            code="IXIC",
            date="2026-05-08",
            pe_ttm=0.0,
            pe_percentile_5y=0.0,
            pb_lf=0.0,
            pb_percentile_5y=0.0,
            dividend_yield=0.0,
            dividend_yield_percentile_5y=0.0,
        )
        cleaned = clean_valuation(raw)
        assert cleaned.pe_ttm is None
        assert cleaned.pb_lf is None
        assert cleaned.pe_percentile_5y is None
        assert cleaned.pb_percentile_5y is None
        assert cleaned.dividend_yield == 0.0
        assert cleaned.dividend_yield_percentile_5y == 0.0

    def test_none_values_stay_none(self) -> None:
        raw = IndexValuation(code="IXIC", date="2026-05-08")
        cleaned = clean_valuation(raw)
        assert cleaned.pe_ttm is None
        assert cleaned.pb_lf is None
        assert cleaned.dividend_yield is None

    def test_negative_pe_becomes_none(self) -> None:
        raw = IndexValuation(
            code="test",
            date="2026-05-08",
            pe_ttm=-5.0,
            pe_percentile_5y=10.0,
        )
        cleaned = clean_valuation(raw)
        assert cleaned.pe_ttm is None
        assert cleaned.pe_percentile_5y is None

    def test_zero_dividend_yield_stays_zero(self) -> None:
        raw = IndexValuation(
            code="test",
            date="2026-05-08",
            dividend_yield=0.0,
            dividend_yield_percentile_5y=50.0,
        )
        cleaned = clean_valuation(raw)
        assert cleaned.dividend_yield == 0.0
        assert cleaned.dividend_yield_percentile_5y == pytest.approx(50.0)

    def test_percentile_none_when_absolute_is_none(self) -> None:
        raw = IndexValuation(
            code="test",
            date="2026-05-08",
            pe_ttm=0.0,
            pe_percentile_5y=30.0,
        )
        cleaned = clean_valuation(raw)
        assert cleaned.pe_ttm is None
        assert cleaned.pe_percentile_5y is None

    def test_nan_values_become_none(self) -> None:
        raw = IndexValuation(
            code="test",
            date="2026-05-08",
            pe_ttm=float("nan"),
            pe_percentile_5y=float("nan"),
            pb_lf=float("nan"),
            dividend_yield=float("nan"),
        )
        cleaned = clean_valuation(raw)
        assert cleaned.pe_ttm is None
        assert cleaned.pe_percentile_5y is None
        assert cleaned.pb_lf is None
        assert cleaned.dividend_yield is None


class TestFetchWithRetry:
    def test_success_on_first_try(self) -> None:
        fn = MagicMock(return_value="ok")
        result = fetch_with_retry(fn, "arg1")
        assert result == "ok"
        fn.assert_called_once_with("arg1")

    @patch("index_score.data.fallback.time.sleep")
    def test_success_after_retries(self, mock_sleep: Any) -> None:
        fn = MagicMock(side_effect=[FetchError("fail1"), FetchError("fail2"), "ok"])
        result = fetch_with_retry(fn)
        assert result == "ok"
        assert fn.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("index_score.data.fallback.time.sleep")
    def test_all_retries_fail_raises(self, mock_sleep: Any) -> None:
        fn = MagicMock(side_effect=FetchError("persistent failure"))
        with pytest.raises(FetchError, match="persistent failure"):
            fetch_with_retry(fn)
        assert fn.call_count == 3
        assert mock_sleep.call_count == 2


class TestFetchAll:
    @patch("index_score.data.fallback.fetch_valuation")
    @patch("index_score.data.fallback.fetch_price_history")
    def test_success_returns_fetch_result(self, mock_price: Any, mock_val: Any) -> None:
        mock_price.return_value = [
            IndexQuote(
                code="000922",
                name="中证红利",
                date="2026-05-08",
                open=4000.0,
                close=4050.0,
                high=4060.0,
                low=3990.0,
                volume=100000000.0,
                adj_close=4050.0,
            )
        ]
        mock_val.return_value = IndexValuation(
            code="000922",
            date="2026-05-08",
            pe_ttm=8.5,
            pe_percentile_5y=30.0,
            dividend_yield=4.5,
            dividend_yield_percentile_5y=20.0,
        )

        result = fetch_all(_cn_index())

        assert isinstance(result, FetchResult)
        assert len(result.quotes) == 1
        assert result.quotes[0].close == pytest.approx(4050.0)
        assert result.valuation.pe_ttm == pytest.approx(8.5)
        assert result.valuation.pe_percentile_5y == pytest.approx(30.0)

    @patch("index_score.data.fallback.fetch_valuation")
    @patch("index_score.data.fallback.fetch_price_history")
    def test_valuation_failure_does_not_block(
        self, mock_price: Any, mock_val: Any
    ) -> None:
        mock_price.return_value = [
            IndexQuote(
                code="000922",
                name="中证红利",
                date="2026-05-08",
                open=100.0,
                close=100.0,
                high=100.0,
                low=100.0,
                volume=100000.0,
                adj_close=100.0,
            )
        ]
        mock_val.side_effect = FetchError("估值拉取失败")

        result = fetch_all(_cn_index())

        assert len(result.quotes) == 1
        assert result.valuation.code == "000922"
        assert result.valuation.pe_ttm is None
        assert result.valuation.pb_lf is None

    @patch("index_score.data.fallback.time.sleep")
    @patch("index_score.data.fallback.fetch_price_history")
    def test_price_failure_raises_after_retries(
        self, mock_price: Any, mock_sleep: Any
    ) -> None:
        mock_price.side_effect = FetchError("行情拉取失败")

        with pytest.raises(FetchError, match="行情拉取失败"):
            fetch_all(_cn_index())
        assert mock_price.call_count == 3

    @patch("index_score.data.fallback.fetch_valuation")
    @patch("index_score.data.fallback.fetch_price_history")
    def test_fetch_all_passes_lixinger_client(
        self, mock_price: Any, mock_val: Any
    ) -> None:
        mock_price.return_value = [
            IndexQuote(
                code="000922",
                name="中证红利",
                date="2026-05-08",
                open=100.0,
                close=100.0,
                high=100.0,
                low=100.0,
                volume=100000.0,
                adj_close=100.0,
            )
        ]
        mock_val.return_value = IndexValuation(
            code="000922",
            date="2026-05-08",
            pe_ttm=8.5,
        )

        mock_client = MagicMock(spec=LixingerClient)
        fetch_all(_cn_index(), lixinger_client=mock_client)

        mock_val.assert_called_once_with(
            _cn_index(),
            client=mock_client,
        )
