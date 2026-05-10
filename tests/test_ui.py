"""UI 组件核心逻辑测试。"""

from __future__ import annotations

from index_score.config.models import FactorScore, IndexScore, IndexValuation
from index_score.ui.app import DataError, DataReady, StatusUpdate
from index_score.ui.widgets.factor_detail import build_detail_content
from index_score.ui.widgets.score_table import score_color


def _score(
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
        date="2026-05-10",
        total_score=total_score,
        label=label,
        factors=[],
    )


def test_score_color_cheap():
    assert score_color(_score(total_score=1.0)) == "green"
    assert score_color(_score(total_score=3.0)) == "green"


def test_score_color_neutral():
    assert score_color(_score(total_score=3.1)) == "yellow"
    assert score_color(_score(total_score=5.0)) == "yellow"
    assert score_color(_score(total_score=6.0)) == "yellow"


def test_score_color_expensive():
    assert score_color(_score(total_score=6.1)) == "red"
    assert score_color(_score(total_score=9.0)) == "red"


def test_score_color_no_data():
    assert score_color(_score(total_score=0.0)) == "grey"


def _score_with_factors() -> IndexScore:
    return IndexScore(
        code="000922",
        name="中证红利",
        template="dividend",
        date="2026-05-10",
        total_score=7.4,
        label="偏贵",
        factors=[
            FactorScore(
                field="dividend_yield_percentile_5y",
                label="便宜",
                percentile=1.7,
                score=1.0,
                weight=0.45,
                original_weight=0.45,
            ),
            FactorScore(
                field="pe_percentile_5y",
                label="极贵",
                percentile=96.7,
                score=9.0,
                weight=0.30,
                original_weight=0.30,
            ),
            FactorScore(
                field="price_position_percentile_3y",
                label="偏贵",
                percentile=83.7,
                score=7.4,
                weight=0.25,
                original_weight=0.25,
            ),
        ],
        price_position_percentile=83.7,
        valuation=IndexValuation(
            code="000922",
            date="2026-05-10",
            pe_ttm=8.74,
            pe_percentile_5y=96.7,
            pb_lf=0.82,
            pb_percentile_5y=93.5,
            dividend_yield=0.041,
            dividend_yield_percentile_5y=1.7,
        ),
    )


def test_build_detail_content_title():
    content = build_detail_content(_score_with_factors(), "test interp")
    assert "中证红利 (000922)" in content
    assert "7.4" in content
    assert "偏贵" in content


def test_build_detail_content_factors():
    content = build_detail_content(_score_with_factors(), "test interp")
    assert "股息率" in content
    assert "PE" in content
    assert "83.7%" in content


def test_build_detail_content_llm():
    interp = "这是一段LLM解读文本"
    content = build_detail_content(_score_with_factors(), interp)
    assert interp in content


def test_build_detail_content_no_llm():
    content = build_detail_content(_score_with_factors(), "")
    assert "暂无 LLM 解读" in content


def test_build_detail_content_no_data():
    s = IndexScore(
        code="999999",
        name="测试指数",
        template="value",
        date="2026-05-10",
        total_score=0.0,
        label="数据不足",
        factors=[],
    )
    content = build_detail_content(s, "")
    assert "数据不足" in content


def test_data_ready_message():
    msg = DataReady(scores=[], interpretations={})
    assert msg.scores == []
    assert msg.interpretations == {}


def test_data_error_message():
    msg = DataError(error="test error")
    assert msg.error == "test error"


def test_status_update_message():
    msg = StatusUpdate(text="loading...")
    assert msg.text == "loading..."


def test_build_detail_content_with_valuation():
    score = _score_with_factors()
    content = build_detail_content(score, "some interpretation")
    assert "8.74" in content
    assert "0.82" in content
    assert "4.10%" in content


def test_build_detail_content_no_valuation():
    s = IndexScore(
        code="000922",
        name="中证红利",
        template="dividend",
        date="2026-05-10",
        total_score=7.4,
        label="偏贵",
        factors=[
            FactorScore(
                field="price_position_percentile_3y",
                label="偏贵",
                percentile=83.7,
                score=7.4,
                weight=1.0,
                original_weight=1.0,
            ),
        ],
        price_position_percentile=83.7,
    )
    content = build_detail_content(s, "test")
    assert "83.7%" in content


def test_get_selected_score_empty():
    from index_score.ui.widgets.score_table import ScoreTable

    table = ScoreTable()
    assert table.get_selected_score() is None
