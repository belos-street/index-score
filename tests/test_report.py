"""报告生成模块测试：模板渲染、文件导出、格式完整性。"""

from __future__ import annotations

from pathlib import Path

from index_score.config.models import FactorScore, IndexScore
from index_score.report.exporter import export_report
from index_score.report.generator import (
    _build_summary,
    _overall_level,
    _sort_scores,
    generate_report,
)


def _score(
    *,
    code: str = "000922",
    name: str = "中证红利",
    template: str = "dividend",
    total_score: float = 3.2,
    label: str = "便宜",
    factors: list[FactorScore] | None = None,
) -> IndexScore:
    if factors is None:
        factors = [
            FactorScore(
                field="dividend_yield_percentile_5y",
                label="便宜",
                percentile=15.2,
                score=1.5,
                weight=0.45,
                original_weight=0.45,
            ),
            FactorScore(
                field="pe_percentile_5y",
                label="中性",
                percentile=55.0,
                score=4.5,
                weight=0.30,
                original_weight=0.30,
            ),
            FactorScore(
                field="price_position_percentile_3y",
                label="便宜",
                percentile=45.3,
                score=3.5,
                weight=0.25,
                original_weight=0.25,
            ),
        ]
    return IndexScore(
        code=code,
        name=name,
        template=template,
        date="2025-05-09",
        total_score=total_score,
        label=label,
        factors=factors,
        price_position_percentile=45.3,
    )


def _three_scores() -> list[IndexScore]:
    return [
        _score(
            code="000922",
            name="中证红利",
            template="dividend",
            total_score=2.6,
            label="便宜",
        ),
        _score(
            code="IXIC",
            name="纳指",
            template="growth",
            total_score=7.5,
            label="偏贵",
        ),
        _score(
            code="SPX",
            name="标普500",
            template="balanced",
            total_score=5.0,
            label="中性",
        ),
    ]


class TestGenerateReport:
    def test_contains_all_sections(self) -> None:
        scores = [_score()]
        report = generate_report(scores, {}, generated_at="2025-05-09 10:00")

        assert "# 大盘指数量化打分报告" in report
        assert "## 摘要" in report
        assert "## 打分明细" in report
        assert "## 指数详细分析" in report
        assert "## 数据来源与声明" in report

    def test_summary_values(self) -> None:
        scores = _three_scores()
        report = generate_report(scores, {}, generated_at="2025-05-09 10:00")

        assert "打分指数数量 | 3" in report
        assert "中证红利 (2.6 分)" in report
        assert "纳指 (7.5 分)" in report

    def test_score_table_structure(self) -> None:
        scores = [_score()]
        report = generate_report(scores, {}, generated_at="2025-05-09 10:00")

        assert "| 排名 | 指数名称 | 模板 |" in report
        assert "| 总分 | 估值水平 |" in report
        assert "| 1 |" in report

    def test_score_table_factor_values(self) -> None:
        scores = [_score()]
        report = generate_report(scores, {}, generated_at="2025-05-09 10:00")

        assert "15.2%(1.5)" in report
        assert "55.0%(4.5)" in report
        assert "45.3%(3.5)" in report

    def test_analyses_contain_title(self) -> None:
        scores = [_score()]
        report = generate_report(scores, {}, generated_at="2025-05-09 10:00")

        assert "中证红利 (000922)" in report
        assert "3.2 分 · 便宜" in report

    def test_llm_interpretation(self) -> None:
        scores = [_score()]
        interps = {"000922": "中证红利当前估值便宜，建议关注。"}
        report = generate_report(scores, interps, generated_at="2025-05-09 10:00")

        assert "中证红利当前估值便宜" in report

    def test_missing_interpretation(self) -> None:
        scores = [_score()]
        report = generate_report(scores, {}, generated_at="2025-05-09 10:00")

        assert "暂无 LLM 解读" in report

    def test_empty_scores(self) -> None:
        report = generate_report([], {}, generated_at="2025-05-09 10:00")

        assert "暂无打分数据" in report
        assert "# 大盘指数量化打分报告" in report

    def test_sort_by_score(self) -> None:
        scores = _three_scores()
        report = generate_report(
            scores,
            {},
            sort_by="score",
            generated_at="2025-05-09 10:00",
        )

        detail_section = report.split("## 指数详细分析")[1]
        pos_dividend = detail_section.index("中证红利")
        pos_spx = detail_section.index("标普500")
        pos_nasdaq = detail_section.index("纳指")
        assert pos_dividend < pos_spx < pos_nasdaq

    def test_sort_by_code(self) -> None:
        scores = _three_scores()
        report = generate_report(
            scores,
            {},
            sort_by="code",
            generated_at="2025-05-09 10:00",
        )

        detail_section = report.split("## 指数详细分析")[1]
        pos_000922 = detail_section.index("000922")
        pos_ixic = detail_section.index("IXIC")
        pos_spx = detail_section.index("SPX")
        assert pos_000922 < pos_ixic < pos_spx

    def test_disclaimer_present(self) -> None:
        scores = [_score()]
        report = generate_report(scores, {}, generated_at="2025-05-09 10:00")

        assert "仅供参考" in report
        assert "不构成投资建议" in report

    def test_generated_at_in_report(self) -> None:
        scores = [_score()]
        report = generate_report(scores, {}, generated_at="2025-05-09 14:30")

        assert "2025-05-09 14:30" in report

    def test_valuation_summary(self) -> None:
        scores = [_score()]
        report = generate_report(scores, {}, generated_at="2025-05-09 10:00")

        assert "股息率分位 15.2%" in report
        assert "PE分位 55.0%" in report
        assert "价格位置 45.3%" in report

    def test_no_factors_report(self) -> None:
        s = _score(total_score=0.0, label="数据不足", factors=[])
        report = generate_report(
            [s],
            {},
            generated_at="2025-05-09 10:00",
        )

        assert "数据不足" in report


class TestBuildSummary:
    def test_valid_scores(self) -> None:
        scores = _three_scores()
        summary = _build_summary(scores)

        assert summary.total_count == 3
        assert summary.avg_score_str == "5.0"
        assert "中证红利" in summary.cheapest_line
        assert "纳指" in summary.most_expensive_line

    def test_empty_valid(self) -> None:
        s = _score(total_score=0.0, label="数据不足")
        summary = _build_summary([s])

        assert summary.total_count == 1
        assert summary.avg_score_str == "N/A"
        assert summary.cheapest_line == "N/A"


class TestOverallLevel:
    def test_cheap(self) -> None:
        assert "便宜" in _overall_level(2.5)

    def test_low(self) -> None:
        assert "偏低" in _overall_level(4.0)

    def test_neutral(self) -> None:
        assert "中性" in _overall_level(5.5)

    def test_high(self) -> None:
        assert "偏高" in _overall_level(7.0)

    def test_expensive(self) -> None:
        assert "偏贵" in _overall_level(8.5)


class TestSortScores:
    def test_sort_by_score(self) -> None:
        scores = _three_scores()
        sorted_s = _sort_scores(scores, "score")

        assert sorted_s[0].code == "000922"
        assert sorted_s[-1].code == "IXIC"

    def test_sort_by_code(self) -> None:
        scores = _three_scores()
        sorted_s = _sort_scores(scores, "code")

        assert sorted_s[0].code == "000922"
        assert sorted_s[1].code == "IXIC"
        assert sorted_s[2].code == "SPX"


class TestExportReport:
    def test_creates_file(self, tmp_path: Path) -> None:
        content = "# Test Report\n\nHello World\n"
        filepath = export_report(
            content,
            date="2025-05-09",
            output_dir=tmp_path,
        )

        assert filepath.exists()
        assert filepath.name == "指数打分报告_20250509.md"
        assert filepath.read_text(encoding="utf-8") == content

    def test_creates_directory(self, tmp_path: Path) -> None:
        subdir = tmp_path / "nested" / "report"
        content = "# Test\n"
        filepath = export_report(
            content,
            date="2025-05-09",
            output_dir=subdir,
        )

        assert filepath.exists()
        assert filepath.parent == subdir

    def test_overwrite_same_day(self, tmp_path: Path) -> None:
        path1 = export_report(
            "# v1",
            date="2025-05-09",
            output_dir=tmp_path,
        )
        path2 = export_report(
            "# v2",
            date="2025-05-09",
            output_dir=tmp_path,
        )

        assert path1 == path2
        assert path2.read_text(encoding="utf-8") == "# v2"

    def test_filename_format(self, tmp_path: Path) -> None:
        filepath = export_report(
            "test",
            date="2026-01-15",
            output_dir=tmp_path,
        )

        assert filepath.name == "指数打分报告_20260115.md"

    def test_uses_current_date(self, tmp_path: Path) -> None:
        filepath = export_report("test", output_dir=tmp_path)

        assert filepath.name.startswith("指数打分报告_")
        assert filepath.name.endswith(".md")

    def test_utf8_content(self, tmp_path: Path) -> None:
        content = "# 大盘指数量化打分报告\n\n中证红利\n"
        filepath = export_report(
            content,
            date="2025-05-09",
            output_dir=tmp_path,
        )

        result = filepath.read_text(encoding="utf-8")
        assert "中证红利" in result


class TestIntegration:
    def test_full_pipeline(self, tmp_path: Path) -> None:
        scores = _three_scores()
        interps = {
            "000922": "红利指数估值便宜。",
            "SPX": "标普500估值中性。",
        }
        report = generate_report(
            scores,
            interps,
            generated_at="2025-05-09 10:00",
        )
        filepath = export_report(
            report,
            date="2025-05-09",
            output_dir=tmp_path,
        )

        content = filepath.read_text(encoding="utf-8")
        assert "# 大盘指数量化打分报告" in content
        assert "打分指数数量 | 3" in content
        assert "红利指数估值便宜" in content
        assert "标普500估值中性" in content
        assert "暂无 LLM 解读" in content
        assert "仅供参考" in content
