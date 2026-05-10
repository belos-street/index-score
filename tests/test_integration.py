"""端到端集成测试：完整流程 + 异常场景。

覆盖链路：配置加载 → 数据拉取 → 清洗 → 打分 → LLM 解读 → 报告生成 → 文件导出。
所有外部依赖（AkShare / 理杏仁 / LLM API）均通过 Mock 隔离。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from index_score.config.exceptions import ConfigError
from index_score.config.loader import load_config
from index_score.data.exceptions import FetchError
from index_score.data.fallback import fetch_all
from index_score.data.lixinger import LixingerClient
from index_score.llm.agent import interpret_direct
from index_score.report.exporter import export_report
from index_score.report.generator import generate_report
from index_score.scoring.calculator import (
    calculate_index_score,
    calculate_price_position,
)


def _write_config(tmp_path: Path) -> Path:
    content = """\
indexes:
  - code: "000922"
    name: "中证红利"
    market: "CN"
    template: "dividend"
    lixinger_code: "000922"
  - code: "399371"
    name: "国证价值100"
    market: "CN"
    template: "value"
    lixinger_code: "399371"
  - code: "IXIC"
    name: "纳指"
    market: "US"
    template: "growth"

scoring:
  templates:
    dividend:
      factors:
        - { field: "dividend_yield_percentile_5y", weight: 0.45 }
        - { field: "pe_percentile_5y", weight: 0.30 }
        - { field: "price_position_percentile_3y", weight: 0.25 }
    value:
      factors:
        - { field: "pe_percentile_5y", weight: 0.40 }
        - { field: "pb_percentile_5y", weight: 0.30 }
        - { field: "dividend_yield_percentile_5y", weight: 0.30 }
    growth:
      factors:
        - { field: "pe_percentile_5y", weight: 0.50 }
        - { field: "price_position_percentile_3y", weight: 0.40 }
        - { field: "dividend_yield_percentile_5y", weight: 0.10 }
  pe_percentile_years: 5
  dividend_yield_percentile_years: 5
  price_position_years: 3

score_ranges:
  - max_percentile: 20
    score: 1
  - max_percentile: 40
    score: 3
  - max_percentile: 60
    score: 5
  - max_percentile: 80
    score: 7
  - max_percentile: 100
    score: 9

llm:
  provider: "deepseek"
  model: "deepseek-v4-flash"
  api_key_env: "INDEX_SCORE_LLM_API_KEY"
  base_url: "https://api.deepseek.com"
  timeout: 30

lixinger:
  token_env: "LIXINGER_TOKEN"
  base_url: "https://open.lixinger.com/api"
  timeout: 30

report:
  show_detail: true
  sort_by: "score"
"""
    p = tmp_path / "config.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def _make_price_df(dates: list[str], closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": dates,
            "open": [c - 10 for c in closes],
            "close": closes,
            "high": [c + 20 for c in closes],
            "low": [c - 20 for c in closes],
            "volume": [1e8] * len(dates),
        }
    )


def _a_share_price_df() -> pd.DataFrame:
    dates = [f"2024-06-{d:02d}" for d in range(1, 21)]
    closes = [3000 + i * 5 for i in range(20)]
    return _make_price_df(dates, closes)


def _us_price_df() -> pd.DataFrame:
    dates = [f"2024-06-{d:02d}" for d in range(1, 21)]
    closes = [15000 + i * 50 for i in range(20)]
    df = _make_price_df(dates, closes)
    df["amount"] = 0
    return df


def _lixinger_response_dividend() -> list[dict[str, Any]]:
    return [
        {
            "date": "2026-05-08T00:00:00.000Z",
            "pe_ttm.mcw": 7.2,
            "pb.mcw": 0.75,
            "dyr.mcw": 0.055,
            "pe_ttm.y5.mcw.cvpos": 0.12,
            "pb.y5.mcw.cvpos": 0.08,
            "dyr.y5.mcw.cvpos": 0.15,
        }
    ]


def _lixinger_response_value() -> list[dict[str, Any]]:
    return [
        {
            "date": "2026-05-08T00:00:00.000Z",
            "pe_ttm.mcw": 9.5,
            "pb.mcw": 0.90,
            "dyr.mcw": 0.038,
            "pe_ttm.y5.mcw.cvpos": 0.32,
            "pb.y5.mcw.cvpos": 0.28,
            "dyr.y5.mcw.cvpos": 0.55,
        }
    ]


def _lixinger_response_growth() -> list[dict[str, Any]]:
    return [
        {
            "date": "2026-05-08T00:00:00.000Z",
            "pe_ttm.mcw": 35.0,
            "pb.mcw": 6.5,
            "dyr.mcw": 0.006,
            "pe_ttm.y5.mcw.cvpos": 0.72,
            "pb.y5.mcw.cvpos": 0.68,
            "dyr.y5.mcw.cvpos": 0.40,
        }
    ]


_LIXINGER_RESPONSES: dict[str, list[dict[str, Any]]] = {
    "000922": _lixinger_response_dividend(),
    "399371": _lixinger_response_value(),
    "IXIC": _lixinger_response_growth(),
}


def _mock_lixinger_fetch(
    stock_codes: list[str],
    date: str | None = None,
    metrics_list: list[str] | None = None,
) -> list[dict[str, Any]]:
    code = stock_codes[0]
    resp = _LIXINGER_RESPONSES.get(code)
    if resp is None:
        return []
    return resp


def _mock_llm_response(content: str = "这是LLM生成的投资解读。") -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.content = content
    return mock_resp


def _run_pipeline(
    config_path: Path,
    *,
    mock_tx: Any,
    mock_us: Any,
    mock_lixinger: Any,
    mock_llm_invoke: Any,
) -> tuple[list, dict[str, str], str, Path]:
    """执行完整 pipeline，返回 (scores, interpretations, report, filepath)。"""
    config = load_config(config_path)

    lixinger_client = MagicMock(spec=LixingerClient)
    lixinger_client.fetch_fundamental = mock_lixinger

    scores = []
    for idx_info in config.indexes:
        result = fetch_all(
            idx_info,
            lixinger_client=lixinger_client,
            price_years=config.scoring.price_position_years,
        )
        pp = calculate_price_position(
            result.quotes, config.scoring.price_position_years
        )
        score = calculate_index_score(
            idx_info,
            result.valuation,
            pp,
            config.scoring,
            config.score_ranges,
        )
        scores.append(score)

    interpretations: dict[str, str] = {}
    mock_llm = MagicMock()
    mock_llm.invoke = mock_llm_invoke
    for s in scores:
        if s.total_score > 0:
            interp = interpret_direct(mock_llm, s)
            interpretations[s.code] = interp

    sort_by = config.report.sort_by if config.report else "score"
    report = generate_report(scores, interpretations, sort_by=sort_by)
    filepath = export_report(report, output_dir=config_path.parent / "report")

    return scores, interpretations, report, filepath


class TestFullPipeline:
    """完整流程集成测试：配置 → 数据 → 打分 → LLM → 报告 → 导出。"""

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_all_indexes_scored_and_reported(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        scores, interps, report, filepath = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        assert len(scores) == 3
        for s in scores:
            assert s.total_score > 0
            assert s.label != "数据不足"
            assert len(s.factors) >= 2

        assert len(interps) == 3
        for code in ["000922", "399371", "IXIC"]:
            assert code in interps

        assert "# 大盘指数量化打分报告" in report
        assert "## 摘要" in report
        assert "## 打分明细" in report
        assert "## 指数详细分析" in report
        assert "## 数据来源与声明" in report

        assert filepath.exists()
        assert filepath.name.startswith("指数打分报告_")
        assert filepath.suffix == ".md"

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_dividend_index_cheap(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        scores, _, _, _ = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        dividend_score = next(s for s in scores if s.code == "000922")
        assert dividend_score.total_score < 5.0

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_growth_index_expensive(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        scores, _, _, _ = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        growth_score = next(s for s in scores if s.code == "IXIC")
        assert growth_score.total_score > 5.0

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_report_contains_all_index_names(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        _, _, report, _ = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        assert "中证红利" in report
        assert "国证价值100" in report
        assert "纳指" in report

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_report_score_table_has_factor_values(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        _, _, report, _ = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        assert "PE分位" in report
        assert "股息率分位" in report

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_report_sorted_by_score_ascending(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        scores, _, report, _ = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        sorted_scores = sorted(scores, key=lambda s: s.total_score)
        detail_section = report.split("## 指数详细分析")[1]
        positions = []
        for s in sorted_scores:
            pos = detail_section.index(s.name)
            positions.append(pos)
        assert positions == sorted(positions)

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_report_disclaimer_present(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        _, _, report, _ = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        assert "仅供参考" in report
        assert "不构成投资建议" in report

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_llm_interpretation_in_report(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)
        mock_llm = MagicMock(
            return_value=_mock_llm_response("中证红利估值便宜，建议关注。")
        )

        _, _, report, _ = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        assert "中证红利估值便宜" in report

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_factor_details_in_score(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        scores, _, _, _ = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        dividend = next(s for s in scores if s.code == "000922")
        factor_fields = {f.field for f in dividend.factors}
        assert "dividend_yield_percentile_5y" in factor_fields
        assert "pe_percentile_5y" in factor_fields
        assert "price_position_percentile_3y" in factor_fields

        for f in dividend.factors:
            assert 1.0 <= f.score <= 9.0
            assert 0.0 < f.weight <= 1.0

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_weights_sum_to_one(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        scores, _, _, _ = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        for s in scores:
            if s.factors:
                total_weight = sum(f.weight for f in s.factors)
                assert total_weight == pytest.approx(1.0, abs=0.01)


class TestPartialDataMissing:
    """部分数据缺失场景：估值降级、权重重分配。"""

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_lixinger_returns_empty_for_one_index(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()

        def partial_lixinger(
            stock_codes: list[str],
            date: str | None = None,
            metrics_list: list[str] | None = None,
        ) -> list[dict[str, Any]]:
            code = stock_codes[0]
            if code == "000922":
                return []
            return _LIXINGER_RESPONSES.get(code, [])

        mock_lixinger = MagicMock(side_effect=partial_lixinger)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        scores, interps, report, _ = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        assert len(scores) == 3

        dividend = next(s for s in scores if s.code == "000922")
        has_valuation_factor = any(
            f.field in ("pe_percentile_5y", "dividend_yield_percentile_5y")
            for f in dividend.factors
        )
        assert not has_valuation_factor

        assert "中证红利" in report

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_lixinger_api_exception_does_not_crash(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()

        def failing_lixinger(
            stock_codes: list[str],
            date: str | None = None,
            metrics_list: list[str] | None = None,
        ) -> list[dict[str, Any]]:
            code = stock_codes[0]
            if code == "000922":
                raise ConnectionError("理杏仁 API 连接超时")
            return _LIXINGER_RESPONSES.get(code, [])

        mock_lixinger = MagicMock(side_effect=failing_lixinger)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        scores, _, report, _ = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        assert len(scores) >= 2
        assert "国证价值100" in report
        assert "纳指" in report

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_weight_redistribution_when_one_factor_missing(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()

        def partial_lixinger(
            stock_codes: list[str],
            date: str | None = None,
            metrics_list: list[str] | None = None,
        ) -> list[dict[str, Any]]:
            code = stock_codes[0]
            if code == "000922":
                return [
                    {
                        "date": "2026-05-08T00:00:00.000Z",
                        "pe_ttm.mcw": 7.2,
                        "pb.mcw": 0.75,
                        "dyr.mcw": None,
                        "pe_ttm.y5.mcw.cvpos": 0.18,
                        "pb.y5.mcw.cvpos": 0.12,
                        "dyr.y5.mcw.cvpos": None,
                    }
                ]
            return _LIXINGER_RESPONSES.get(code, [])

        mock_lixinger = MagicMock(side_effect=partial_lixinger)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        scores, _, _, _ = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        dividend = next(s for s in scores if s.code == "000922")
        factor_fields = {f.field for f in dividend.factors}
        assert "dividend_yield_percentile_5y" not in factor_fields

        total_weight = sum(f.weight for f in dividend.factors)
        assert total_weight == pytest.approx(1.0, abs=0.01)


class TestAPIFailure:
    """API 失败场景：行情拉取失败、估值 API 不可用。"""

    @patch("index_score.data.fetcher.ak.stock_zh_index_daily")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_all_price_sources_fail(
        self,
        mock_tx: MagicMock,
        mock_sina: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = pd.DataFrame()
        mock_sina.return_value = pd.DataFrame()

        config = load_config(config_path)
        cn_index = config.indexes[0]

        with pytest.raises(FetchError, match="所有A股行情数据源均失败"):
            fetch_all(
                cn_index,
                lixinger_client=None,
                price_years=3,
            )

    @patch("index_score.data.fetcher.ak.stock_zh_index_daily")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_price_network_error(
        self,
        mock_tx: MagicMock,
        mock_sina: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.side_effect = ConnectionError("网络超时")
        mock_sina.side_effect = ConnectionError("网络超时")

        config = load_config(config_path)
        cn_index = config.indexes[0]

        with pytest.raises(FetchError):
            fetch_all(
                cn_index,
                lixinger_client=None,
                price_years=3,
            )

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_partial_index_failure_others_succeed(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.side_effect = ConnectionError("美股 API 不可用")
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)

        config = load_config(config_path)
        lixinger_client = MagicMock(spec=LixingerClient)
        lixinger_client.fetch_fundamental = mock_lixinger

        scores = []
        for idx_info in config.indexes:
            try:
                result = fetch_all(
                    idx_info,
                    lixinger_client=lixinger_client,
                    price_years=3,
                )
                pp = calculate_price_position(result.quotes, 3)
                score = calculate_index_score(
                    idx_info,
                    result.valuation,
                    pp,
                    config.scoring,
                    config.score_ranges,
                )
                scores.append(score)
            except FetchError:
                pass

        assert len(scores) == 2
        codes = {s.code for s in scores}
        assert "000922" in codes
        assert "399371" in codes
        assert "IXIC" not in codes


class TestLLMFailure:
    """LLM 异常场景：超时、API 错误、空返回 → 兜底文本。"""

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_llm_timeout_produces_fallback(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)

        config = load_config(config_path)
        lixinger_client = MagicMock(spec=LixingerClient)
        lixinger_client.fetch_fundamental = mock_lixinger

        scores = []
        for idx_info in config.indexes:
            result = fetch_all(
                idx_info,
                lixinger_client=lixinger_client,
                price_years=3,
            )
            pp = calculate_price_position(result.quotes, 3)
            score = calculate_index_score(
                idx_info,
                result.valuation,
                pp,
                config.scoring,
                config.score_ranges,
            )
            scores.append(score)

        mock_llm_obj = MagicMock()
        mock_llm_obj.invoke.side_effect = TimeoutError("LLM 请求超时")

        interpretations: dict[str, str] = {}
        for s in scores:
            interp = interpret_direct(mock_llm_obj, s)
            interpretations[s.code] = interp

        assert len(interpretations) == 3
        for interp in interpretations.values():
            assert "仅供参考" in interp
            assert "不构成投资建议" in interp

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_llm_empty_response_produces_fallback(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)

        empty_resp = MagicMock()
        empty_resp.content = ""
        mock_llm = MagicMock(return_value=empty_resp)

        config = load_config(config_path)
        lixinger_client = MagicMock(spec=LixingerClient)
        lixinger_client.fetch_fundamental = mock_lixinger

        scores = []
        for idx_info in config.indexes:
            result = fetch_all(
                idx_info,
                lixinger_client=lixinger_client,
                price_years=3,
            )
            pp = calculate_price_position(result.quotes, 3)
            score = calculate_index_score(
                idx_info,
                result.valuation,
                pp,
                config.scoring,
                config.score_ranges,
            )
            scores.append(score)

        mock_llm_obj = MagicMock()
        mock_llm_obj.invoke = mock_llm
        interp = interpret_direct(mock_llm_obj, scores[0])

        assert "仅供参考" in interp

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_llm_failure_report_still_generated(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)

        config = load_config(config_path)
        lixinger_client = MagicMock(spec=LixingerClient)
        lixinger_client.fetch_fundamental = mock_lixinger

        scores = []
        for idx_info in config.indexes:
            result = fetch_all(
                idx_info,
                lixinger_client=lixinger_client,
                price_years=3,
            )
            pp = calculate_price_position(result.quotes, 3)
            score = calculate_index_score(
                idx_info,
                result.valuation,
                pp,
                config.scoring,
                config.score_ranges,
            )
            scores.append(score)

        mock_llm_obj = MagicMock()
        mock_llm_obj.invoke.side_effect = RuntimeError("API 返回 500")

        interpretations: dict[str, str] = {}
        for s in scores:
            interp = interpret_direct(mock_llm_obj, s)
            interpretations[s.code] = interp

        report = generate_report(scores, interpretations, sort_by="score")

        assert "# 大盘指数量化打分报告" in report
        assert "中证红利" in report
        for interp in interpretations.values():
            assert "仅供参考" in interp


class TestAllIndexesFail:
    """所有指数数据拉取失败场景。"""

    @patch("index_score.data.fetcher.ak.stock_zh_index_daily")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    def test_all_data_sources_down(
        self,
        mock_us: MagicMock,
        mock_tx: MagicMock,
        mock_sina: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = pd.DataFrame()
        mock_sina.return_value = pd.DataFrame()
        mock_us.return_value = pd.DataFrame()

        config = load_config(config_path)
        successful = 0
        failed = 0
        for idx_info in config.indexes:
            try:
                fetch_all(idx_info, lixinger_client=None, price_years=3)
                successful += 1
            except FetchError:
                failed += 1

        assert successful == 0
        assert failed == 3

    def test_empty_scores_generates_empty_report(
        self,
        tmp_path: Path,
    ) -> None:
        report = generate_report(
            [], {}, sort_by="score", generated_at="2026-05-10 10:00"
        )

        assert "暂无打分数据" in report
        assert "# 大盘指数量化打分报告" in report

        filepath = export_report(report, date="2026-05-10", output_dir=tmp_path)
        assert filepath.exists()
        assert "暂无打分数据" in filepath.read_text(encoding="utf-8")


class TestConfigValidation:
    """配置文件异常场景。"""

    def test_missing_config_file(self, tmp_path: Path) -> None:
        with pytest.raises(Exception, match="配置文件不存在"):
            load_config(tmp_path / "nonexistent.yaml")

    def test_malformed_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "config.yaml"
        p.write_text("{{{{invalid yaml", encoding="utf-8")
        with pytest.raises(Exception, match="配置文件格式错误"):
            load_config(p)

    def test_missing_required_field(self, tmp_path: Path) -> None:
        p = tmp_path / "config.yaml"
        p.write_text("indexes:\n  - code: test\n", encoding="utf-8")
        with pytest.raises(ConfigError):
            load_config(p)


class TestEndToEndCLI:
    """CLI 入口（main.py）集成测试。"""

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_report_mode_generates_file(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        config_path = _write_config(tmp_path)

        monkeypatch.chdir(tmp_path)

        with (
            patch("index_score.config.loader.load_config") as mock_load,
            patch("index_score.data.lixinger.LixingerClient") as mock_lx_cls,
            patch("index_score.llm.agent.build_llm") as mock_build_llm,
        ):
            config = load_config(config_path)
            mock_load.return_value = config

            mock_lx_instance = MagicMock()
            mock_lx_instance.fetch_fundamental = mock_lixinger
            mock_lx_cls.return_value = mock_lx_instance

            mock_llm_obj = MagicMock()
            mock_llm_obj.invoke = mock_llm
            mock_build_llm.return_value = mock_llm_obj

            from index_score.main import _run_report

            _run_report()

        report_files = list(Path(tmp_path).glob("report/指数打分报告_*.md"))
        assert len(report_files) >= 1
        content = report_files[0].read_text(encoding="utf-8")
        assert "# 大盘指数量化打分报告" in content


class TestReportExportIntegration:
    """报告导出集成测试：文件格式、编码、覆盖。"""

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_report_file_utf8_encoded(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        mock_tx.return_value = _a_share_price_df()
        mock_us.return_value = _us_price_df()
        mock_lixinger = MagicMock(side_effect=_mock_lixinger_fetch)
        mock_llm = MagicMock(return_value=_mock_llm_response())

        _, _, _, filepath = _run_pipeline(
            config_path,
            mock_tx=mock_tx,
            mock_us=mock_us,
            mock_lixinger=mock_lixinger,
            mock_llm_invoke=mock_llm,
        )

        content = filepath.read_text(encoding="utf-8")
        assert "大盘指数量化打分报告" in content
        assert "理杏仁" in content

    @patch("index_score.data.fetcher.ak.index_us_stock_sina")
    @patch("index_score.data.fetcher.ak.stock_zh_index_daily_tx")
    def test_report_overwrite_same_day(
        self,
        mock_tx: MagicMock,
        mock_us: MagicMock,
        tmp_path: Path,
    ) -> None:
        report_dir = tmp_path / "report"

        path1 = export_report("# v1", date="2026-05-10", output_dir=report_dir)
        path2 = export_report("# v2", date="2026-05-10", output_dir=report_dir)

        assert path1 == path2
        assert path2.read_text(encoding="utf-8") == "# v2"
