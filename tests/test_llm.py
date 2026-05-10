"""LLM 模块测试：Prompt 构建、Tools、Agent、兜底文本。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from index_score.config.models import (
    FactorScore,
    IndexScore,
    LLMConfig,
)
from index_score.llm.agent import (
    _build_fallback,
    build_llm,
    interpret_direct,
)
from index_score.llm.prompts import (
    FIELD_LABELS,
    SYSTEM_PROMPT,
    build_interpretation_query,
    format_index_score,
)
from index_score.llm.tools import create_tools


def _sample_score(
    *,
    code: str = "000922",
    name: str = "中证红利",
    template: str = "dividend",
    total_score: float = 3.2,
    label: str = "便宜",
) -> IndexScore:
    return IndexScore(
        code=code,
        name=name,
        template=template,
        date="2025-05-09",
        total_score=total_score,
        label=label,
        factors=[
            FactorScore(
                field="dividend_yield_percentile_5y",
                label="便宜",
                percentile=25.0,
                score=2.5,
                weight=0.45,
                original_weight=0.45,
            ),
            FactorScore(
                field="pe_percentile_5y",
                label="中性",
                percentile=50.0,
                score=4.0,
                weight=0.30,
                original_weight=0.30,
            ),
            FactorScore(
                field="price_position_percentile_3y",
                label="便宜",
                percentile=30.0,
                score=2.2,
                weight=0.25,
                original_weight=0.25,
            ),
        ],
        price_position_percentile=30.0,
    )


def _minimal_score() -> IndexScore:
    return IndexScore(
        code="IXIC",
        name="纳指",
        template="growth",
        date="2025-05-09",
        total_score=0.0,
        label="数据不足",
        factors=[],
    )


def _llm_config(
    *,
    model: str = "deepseek-v4-flash",
    api_key: str = "sk-test123",
) -> LLMConfig:
    return LLMConfig(
        provider="deepseek",
        model=model,
        api_key_env="TEST_LLM_KEY",
        base_url="https://api.deepseek.com",
        timeout=30,
    )


class TestFormatIndexScore:
    def test_basic_fields(self) -> None:
        score = _sample_score()
        text = format_index_score(score)

        assert "中证红利" in text
        assert "000922" in text
        assert "dividend" in text
        assert "2025-05-09" in text
        assert "3.2" in text
        assert "便宜" in text

    def test_factor_details(self) -> None:
        score = _sample_score()
        text = format_index_score(score)

        for field, label in FIELD_LABELS.items():
            if field in [f.field for f in score.factors]:
                assert label in text

        assert "25.0%" in text
        assert "50.0%" in text
        assert "30.0%" in text

    def test_price_position(self) -> None:
        score = _sample_score()
        text = format_index_score(score)
        assert "30.0%" in text
        assert "3年窗口" in text

    def test_no_factors(self) -> None:
        score = _minimal_score()
        text = format_index_score(score)
        assert "数据不足" in text

    def test_no_price_position(self) -> None:
        score = IndexScore(
            code="TEST",
            name="测试指数",
            template="balanced",
            date="2025-01-01",
            total_score=5.0,
            label="中性",
            factors=[],
            price_position_percentile=None,
        )
        text = format_index_score(score)
        assert "3年窗口" not in text


class TestBuildInterpretationQuery:
    def test_contains_score_info(self) -> None:
        score = _sample_score()
        query = build_interpretation_query(score)

        assert "估值情况" in query
        assert "中证红利" in query
        assert "3.2" in query

    def test_minimal_score(self) -> None:
        query = build_interpretation_query(_minimal_score())
        assert "纳指" in query
        assert "IXIC" in query


class TestSystemPrompt:
    def test_contains_scoring_rules(self) -> None:
        assert "1.0~9.0" in SYSTEM_PROMPT
        assert "极便宜" in SYSTEM_PROMPT
        assert "极贵" in SYSTEM_PROMPT

    def test_contains_tool_names(self) -> None:
        assert "get_index_score" in SYSTEM_PROMPT
        assert "list_all_scores" in SYSTEM_PROMPT

    def test_contains_output_requirements(self) -> None:
        assert "估值水平判断" in SYSTEM_PROMPT
        assert "各因子解读" in SYSTEM_PROMPT
        assert "投资建议" in SYSTEM_PROMPT


class TestTools:
    def test_get_index_score_found(self) -> None:
        scores = [_sample_score()]
        tools = create_tools(scores)
        get_score = tools[0]

        result = get_score.invoke({"code": "000922"})
        assert "中证红利" in result
        assert "3.2" in result

    def test_get_index_score_not_found(self) -> None:
        scores = [_sample_score()]
        tools = create_tools(scores)
        get_score = tools[0]

        result = get_score.invoke({"code": "XXXXXX"})
        assert "未找到" in result
        assert "000922" in result

    def test_get_index_score_empty(self) -> None:
        tools = create_tools([])
        get_score = tools[0]

        result = get_score.invoke({"code": "000922"})
        assert "未找到" in result

    def test_list_all_scores_sorted(self) -> None:
        scores = [
            _sample_score(code="000922", name="中证红利", total_score=3.2),
            _sample_score(code="IXIC", name="纳指", total_score=7.5),
            _sample_score(code="SPX", name="标普500", total_score=5.0),
        ]
        tools = create_tools(scores)
        list_fn = tools[1]

        result = list_fn.invoke({})
        lines = result.strip().split("\n")
        detail_lines = [ln for ln in lines if ln.startswith("-")]
        assert len(detail_lines) == 3
        assert detail_lines.index(
            next(ln for ln in detail_lines if "中证红利" in ln)
        ) < detail_lines.index(next(ln for ln in detail_lines if "标普500" in ln))

    def test_list_all_scores_empty(self) -> None:
        tools = create_tools([])
        list_fn = tools[1]

        result = list_fn.invoke({})
        assert "没有" in result

    def test_compare_indexes_stub(self) -> None:
        tools = create_tools([])
        compare = tools[2]

        result = compare.invoke({"codes": "000922,IXIC"})
        assert "V2" in result

    def test_generate_report_stub(self) -> None:
        tools = create_tools([])
        report = tools[3]

        result = report.invoke({"code": "000922"})
        assert "V2" in result

    def test_tools_count(self) -> None:
        tools = create_tools([])
        assert len(tools) == 4


class TestBuildLLM:
    def test_raises_without_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEST_LLM_KEY", raising=False)
        config = _llm_config(api_key="")

        with pytest.raises(ValueError, match="API Key 未配置"):
            build_llm(config)

    @patch("index_score.llm.agent.ChatOpenAI")
    def test_creates_with_config(self, mock_cls: MagicMock) -> None:
        config = LLMConfig(
            provider="deepseek",
            model="deepseek-v4-flash",
            api_key_env="TEST_KEY",
            base_url="https://api.deepseek.com",
            timeout=30,
        )
        with patch.dict("os.environ", {"TEST_KEY": "sk-abc"}):
            build_llm(config)

        mock_cls.assert_called_once_with(
            model="deepseek-v4-flash",
            api_key="sk-abc",
            base_url="https://api.deepseek.com",
            timeout=30,
        )


class TestInterpretDirect:
    @patch("index_score.llm.agent.ChatOpenAI")
    def test_success(self, mock_cls: MagicMock) -> None:
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "中证红利当前估值便宜，建议关注。"
        mock_llm.invoke.return_value = mock_response

        result = interpret_direct(mock_llm, _sample_score())
        assert "便宜" in result
        assert "建议" in result
        mock_llm.invoke.assert_called_once()

    @patch("index_score.llm.agent.ChatOpenAI")
    def test_empty_response_fallback(self, mock_cls: MagicMock) -> None:
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = ""
        mock_llm.invoke.return_value = mock_response

        result = interpret_direct(mock_llm, _sample_score())
        assert "中证红利" in result
        assert "3.2" in result
        assert "仅供参考" in result

    @patch("index_score.llm.agent.ChatOpenAI")
    def test_api_failure_fallback(self, mock_cls: MagicMock) -> None:
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = ConnectionError("timeout")

        result = interpret_direct(mock_llm, _sample_score())
        assert "中证红利" in result
        assert "3.2" in result
        assert "仅供参考" in result

    @patch("index_score.llm.agent.ChatOpenAI")
    def test_fallback_contains_factors(self, mock_cls: MagicMock) -> None:
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = RuntimeError("fail")

        result = interpret_direct(mock_llm, _sample_score())
        assert "dividend_yield_percentile_5y" in result
        assert "便宜" in result


class TestBuildFallback:
    def test_with_factors(self) -> None:
        score = _sample_score()
        text = _build_fallback(score)

        assert "中证红利" in text
        assert "000922" in text
        assert "3.2" in text
        assert "便宜" in text
        assert "仅供参考" in text
        assert "dividend_yield_percentile_5y" in text
        assert "pe_percentile_5y" in text
        assert "price_position_percentile_3y" in text

    def test_without_factors(self) -> None:
        score = _minimal_score()
        text = _build_fallback(score)

        assert "纳指" in text
        assert "数据不足" in text
        assert "仅供参考" in text

    def test_score_format(self) -> None:
        score = _sample_score(total_score=7.8, label="偏贵")
        text = _build_fallback(score)
        assert "7.8" in text
        assert "偏贵" in text
