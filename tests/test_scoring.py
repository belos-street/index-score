"""打分模块测试：因子插值、标签、价格位置、综合打分。"""

from __future__ import annotations

import pytest

from index_score.config.models import (
    FactorConfig,
    IndexInfo,
    IndexQuote,
    IndexScore,
    IndexValuation,
    ScoreRange,
    ScoringConfig,
    ScoringTemplate,
)
from index_score.scoring.calculator import (  # noqa: I001
    calculate_index_score,
    calculate_price_position,
)
from index_score.scoring.factor import percentile_to_score, score_to_label


def _default_ranges() -> list[ScoreRange]:
    return [
        ScoreRange(max_percentile=20, score=1),
        ScoreRange(max_percentile=40, score=3),
        ScoreRange(max_percentile=60, score=5),
        ScoreRange(max_percentile=80, score=7),
        ScoreRange(max_percentile=100, score=9),
    ]


def _dividend_template() -> ScoringTemplate:
    return ScoringTemplate(
        name="dividend",
        factors=[
            FactorConfig(field="dividend_yield_percentile_5y", weight=0.45),
            FactorConfig(field="pe_percentile_5y", weight=0.30),
            FactorConfig(field="price_position_percentile_3y", weight=0.25),
        ],
    )


def _value_template() -> ScoringTemplate:
    return ScoringTemplate(
        name="value",
        factors=[
            FactorConfig(field="pe_percentile_5y", weight=0.40),
            FactorConfig(field="pb_percentile_5y", weight=0.30),
            FactorConfig(field="dividend_yield_percentile_5y", weight=0.30),
        ],
    )


def _growth_template() -> ScoringTemplate:
    return ScoringTemplate(
        name="growth",
        factors=[
            FactorConfig(field="pe_percentile_5y", weight=0.50),
            FactorConfig(field="price_position_percentile_3y", weight=0.40),
            FactorConfig(field="dividend_yield_percentile_5y", weight=0.10),
        ],
    )


def _balanced_template() -> ScoringTemplate:
    return ScoringTemplate(
        name="balanced",
        factors=[
            FactorConfig(field="pe_percentile_5y", weight=0.35),
            FactorConfig(field="dividend_yield_percentile_5y", weight=0.35),
            FactorConfig(field="price_position_percentile_3y", weight=0.30),
        ],
    )


def _scoring_config() -> ScoringConfig:
    return ScoringConfig(
        templates={
            "dividend": _dividend_template(),
            "value": _value_template(),
            "growth": _growth_template(),
            "balanced": _balanced_template(),
        },
        pe_percentile_years=5,
        dividend_yield_percentile_years=5,
        price_position_years=3,
    )


def _dividend_index() -> IndexInfo:
    return IndexInfo(code="000922", name="中证红利", market="CN", template="dividend")


def _value_index() -> IndexInfo:
    return IndexInfo(code="399371", name="国证价值100", market="CN", template="value")


def _growth_index() -> IndexInfo:
    return IndexInfo(code="IXIC", name="纳指", market="US", template="growth")


def _balanced_index() -> IndexInfo:
    return IndexInfo(code="SPX", name="标普500", market="US", template="balanced")


def _full_valuation() -> IndexValuation:
    return IndexValuation(
        code="000922",
        date="2026-05-08",
        pe_ttm=12.5,
        pe_percentile_5y=35.0,
        pb_lf=1.2,
        pb_percentile_5y=25.0,
        dividend_yield=4.5,
        dividend_yield_percentile_5y=15.0,
    )


def _make_quotes(
    dates: list[str],
    closes: list[float],
) -> list[IndexQuote]:
    quotes: list[IndexQuote] = []
    for d, c in zip(dates, closes, strict=False):
        quotes.append(
            IndexQuote(
                code="000922",
                name="中证红利",
                date=d,
                open=c - 10,
                close=c,
                high=c + 20,
                low=c - 20,
                volume=100000.0,
                adj_close=c,
            )
        )
    return quotes


class TestPercentileToScore:
    def test_boundary_at_each_range(self) -> None:
        ranges = _default_ranges()

        assert percentile_to_score(0, ranges) == pytest.approx(1.0)
        assert percentile_to_score(20, ranges) == pytest.approx(1.0)
        assert percentile_to_score(40, ranges) == pytest.approx(3.0)
        assert percentile_to_score(60, ranges) == pytest.approx(5.0)
        assert percentile_to_score(80, ranges) == pytest.approx(7.0)
        assert percentile_to_score(100, ranges) == pytest.approx(9.0)

    def test_midpoint_interpolation(self) -> None:
        ranges = _default_ranges()

        assert percentile_to_score(10, ranges) == pytest.approx(1.0)
        assert percentile_to_score(30, ranges) == pytest.approx(2.0)
        assert percentile_to_score(50, ranges) == pytest.approx(4.0)
        assert percentile_to_score(70, ranges) == pytest.approx(6.0)
        assert percentile_to_score(90, ranges) == pytest.approx(8.0)

    def test_quarter_point_interpolation(self) -> None:
        ranges = _default_ranges()

        assert percentile_to_score(25, ranges) == pytest.approx(1.5)
        assert percentile_to_score(35, ranges) == pytest.approx(2.5)
        assert percentile_to_score(55, ranges) == pytest.approx(4.5)
        assert percentile_to_score(75, ranges) == pytest.approx(6.5)
        assert percentile_to_score(85, ranges) == pytest.approx(7.5)

    def test_clamped_at_0_and_100(self) -> None:
        ranges = _default_ranges()

        assert percentile_to_score(-5, ranges) == pytest.approx(1.0)
        assert percentile_to_score(105, ranges) == pytest.approx(9.0)

    def test_single_decimal_precision(self) -> None:
        ranges = _default_ranges()

        score = percentile_to_score(33, ranges)
        assert score == round(score, 1)

    def test_empty_ranges_returns_5(self) -> None:
        assert percentile_to_score(50, []) == pytest.approx(5.0)

    def test_custom_ranges(self) -> None:
        ranges = [
            ScoreRange(max_percentile=50, score=2),
            ScoreRange(max_percentile=100, score=8),
        ]

        assert percentile_to_score(0, ranges) == pytest.approx(2.0)
        assert percentile_to_score(25, ranges) == pytest.approx(2.0)
        assert percentile_to_score(50, ranges) == pytest.approx(2.0)
        assert percentile_to_score(75, ranges) == pytest.approx(5.0)
        assert percentile_to_score(100, ranges) == pytest.approx(8.0)


class TestScoreToLabel:
    def test_exact_thresholds(self) -> None:
        assert score_to_label(1.0) == "极便宜"
        assert score_to_label(2.0) == "极便宜"
        assert score_to_label(3.0) == "便宜"
        assert score_to_label(4.0) == "便宜"
        assert score_to_label(5.0) == "中性"
        assert score_to_label(6.0) == "中性"
        assert score_to_label(7.0) == "偏贵"
        assert score_to_label(8.0) == "偏贵"
        assert score_to_label(9.0) == "极贵"

    def test_between_thresholds(self) -> None:
        assert score_to_label(1.5) == "极便宜"
        assert score_to_label(3.5) == "便宜"
        assert score_to_label(5.5) == "中性"
        assert score_to_label(7.5) == "偏贵"
        assert score_to_label(8.5) == "极贵"


class TestCalculatePricePosition:
    def test_price_at_low(self) -> None:
        dates = [f"2024-01-{d:02d}" for d in range(1, 6)]
        closes = [100.0, 110.0, 120.0, 110.0, 100.0]
        quotes = _make_quotes(dates, closes)

        result = calculate_price_position(quotes, years=3)
        assert result == pytest.approx(0.0)

    def test_price_at_high(self) -> None:
        dates = [f"2024-01-{d:02d}" for d in range(1, 6)]
        closes = [100.0, 110.0, 120.0, 110.0, 200.0]
        quotes = _make_quotes(dates, closes)

        result = calculate_price_position(quotes, years=3)
        assert result == pytest.approx(100.0)

    def test_price_at_midpoint(self) -> None:
        dates = [f"2024-01-{d:02d}" for d in range(1, 6)]
        closes = [100.0, 200.0, 150.0, 110.0, 150.0]
        quotes = _make_quotes(dates, closes)

        result = calculate_price_position(quotes, years=3)
        assert result == pytest.approx(50.0)

    def test_empty_quotes(self) -> None:
        assert calculate_price_position([], years=3) is None

    def test_single_quote(self) -> None:
        quotes = _make_quotes(["2026-05-08"], [100.0])
        assert calculate_price_position(quotes, years=3) is None

    def test_flat_prices(self) -> None:
        dates = [f"2024-01-{d:02d}" for d in range(1, 6)]
        closes = [100.0, 100.0, 100.0, 100.0, 100.0]
        quotes = _make_quotes(dates, closes)

        assert calculate_price_position(quotes, years=3) is None

    def test_quotes_sorted_ascending(self) -> None:
        dates = ["2026-05-01", "2026-05-02", "2026-05-03"]
        closes = [100.0, 150.0, 200.0]
        quotes = _make_quotes(dates, closes)

        result = calculate_price_position(quotes, years=3)
        assert result == pytest.approx(100.0)


class TestCalculateIndexScore:
    def test_dividend_template_all_factors(self) -> None:
        valuation = IndexValuation(
            code="000922",
            date="2026-05-08",
            pe_percentile_5y=30.0,
            dividend_yield_percentile_5y=15.0,
        )
        ranges = _default_ranges()

        result = calculate_index_score(
            _dividend_index(),
            valuation,
            50.0,
            _scoring_config(),
            ranges,
        )

        assert isinstance(result, IndexScore)
        assert result.code == "000922"
        assert result.template == "dividend"
        assert len(result.factors) == 3

    def test_value_template_all_factors(self) -> None:
        valuation = IndexValuation(
            code="399371",
            date="2026-05-08",
            pe_percentile_5y=20.0,
            pb_percentile_5y=30.0,
            dividend_yield_percentile_5y=40.0,
        )
        ranges = _default_ranges()

        result = calculate_index_score(
            _value_index(),
            valuation,
            None,
            _scoring_config(),
            ranges,
        )

        assert result.template == "value"
        assert len(result.factors) == 3

    def test_growth_template_all_factors(self) -> None:
        valuation = IndexValuation(
            code="IXIC",
            date="2026-05-08",
            pe_percentile_5y=60.0,
            dividend_yield_percentile_5y=80.0,
        )
        ranges = _default_ranges()

        result = calculate_index_score(
            _growth_index(),
            valuation,
            45.0,
            _scoring_config(),
            ranges,
        )

        assert result.template == "growth"
        assert len(result.factors) == 3

    def test_balanced_template_all_factors(self) -> None:
        valuation = IndexValuation(
            code="SPX",
            date="2026-05-08",
            pe_percentile_5y=55.0,
            dividend_yield_percentile_5y=65.0,
        )
        ranges = _default_ranges()

        result = calculate_index_score(
            _balanced_index(),
            valuation,
            40.0,
            _scoring_config(),
            ranges,
        )

        assert result.template == "balanced"
        assert len(result.factors) == 3

    def test_score_range_1_to_9(self) -> None:
        cheap = IndexValuation(
            code="000922",
            date="2026-05-08",
            pe_percentile_5y=5.0,
            dividend_yield_percentile_5y=5.0,
        )
        ranges = _default_ranges()

        cheap_result = calculate_index_score(
            _dividend_index(), cheap, 5.0, _scoring_config(), ranges
        )
        assert 1.0 <= cheap_result.total_score <= 9.0

        expensive = IndexValuation(
            code="000922",
            date="2026-05-08",
            pe_percentile_5y=95.0,
            dividend_yield_percentile_5y=95.0,
        )
        expensive_result = calculate_index_score(
            _dividend_index(), expensive, 95.0, _scoring_config(), ranges
        )
        assert 1.0 <= expensive_result.total_score <= 9.0
        assert expensive_result.total_score > cheap_result.total_score

    def test_score_is_one_decimal(self) -> None:
        valuation = IndexValuation(
            code="000922",
            date="2026-05-08",
            pe_percentile_5y=33.0,
            dividend_yield_percentile_5y=55.0,
        )
        result = calculate_index_score(
            _dividend_index(),
            valuation,
            77.0,
            _scoring_config(),
            _default_ranges(),
        )
        assert result.total_score == round(result.total_score, 1)

    def test_weight_redistribution_when_one_factor_missing(self) -> None:
        valuation = IndexValuation(
            code="000922",
            date="2026-05-08",
            pe_percentile_5y=30.0,
            dividend_yield_percentile_5y=15.0,
        )
        ranges = _default_ranges()

        result = calculate_index_score(
            _dividend_index(),
            valuation,
            None,
            _scoring_config(),
            ranges,
        )

        assert len(result.factors) == 2

        total_weight = sum(f.weight for f in result.factors)
        assert total_weight == pytest.approx(1.0, abs=0.001)

        div_factor = next(
            f for f in result.factors if f.field == "dividend_yield_percentile_5y"
        )
        pe_factor = next(f for f in result.factors if f.field == "pe_percentile_5y")
        assert div_factor.weight == pytest.approx(0.45 / (0.45 + 0.30), abs=0.001)
        assert pe_factor.weight == pytest.approx(0.30 / (0.45 + 0.30), abs=0.001)

        assert div_factor.original_weight == pytest.approx(0.45)
        assert pe_factor.original_weight == pytest.approx(0.30)

    def test_weight_redistribution_two_factors_missing(self) -> None:
        valuation = IndexValuation(
            code="000922",
            date="2026-05-08",
            pe_percentile_5y=None,
            dividend_yield_percentile_5y=15.0,
        )
        ranges = _default_ranges()

        result = calculate_index_score(
            _dividend_index(),
            valuation,
            None,
            _scoring_config(),
            ranges,
        )

        assert len(result.factors) == 1
        assert result.factors[0].weight == pytest.approx(1.0)

    def test_all_factors_missing(self) -> None:
        valuation = IndexValuation(
            code="000922",
            date="2026-05-08",
        )
        ranges = _default_ranges()

        result = calculate_index_score(
            _dividend_index(),
            valuation,
            None,
            _scoring_config(),
            ranges,
        )

        assert result.total_score == 0.0
        assert result.label == "数据不足"
        assert result.factors == []

    def test_factor_score_label_matches_score(self) -> None:
        valuation = IndexValuation(
            code="000922",
            date="2026-05-08",
            pe_percentile_5y=90.0,
            dividend_yield_percentile_5y=10.0,
        )
        result = calculate_index_score(
            _dividend_index(),
            valuation,
            50.0,
            _scoring_config(),
            _default_ranges(),
        )

        for fs in result.factors:
            expected_label = score_to_label(fs.score)
            assert fs.label == expected_label
