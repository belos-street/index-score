"""CLI 入口。

默认启动 Textual 终端界面。
传入 --report 则直接生成 Markdown 报告，不进入交互式 UI。
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _run_report() -> None:
    """拉取数据 → 打分 → LLM 解读 → 生成报告（纯命令行）。"""
    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
    except ImportError:
        pass

    from index_score.config.loader import load_config
    from index_score.data.fallback import fetch_all
    from index_score.data.lixinger import LixingerClient
    from index_score.llm.agent import build_llm, interpret_direct
    from index_score.report.exporter import export_report
    from index_score.report.generator import generate_report
    from index_score.scoring.calculator import (
        calculate_index_score,
        calculate_price_position,
    )

    project_root = Path(__file__).resolve().parent.parent.parent
    config = load_config(project_root / "config.yaml")

    lixinger_client = None
    if config.lixinger and config.lixinger.token:
        lixinger_client = LixingerClient(config.lixinger)
        print("理杏仁 API 已连接")
    else:
        print("警告：理杏仁 Token 未配置，估值数据可能缺失")

    price_years = config.scoring.price_position_years
    scores = []

    for idx_info in config.indexes:
        print(f"\n拉取数据: {idx_info.name} ({idx_info.code})...")
        try:
            result = fetch_all(
                idx_info,
                lixinger_client=lixinger_client,
                price_years=price_years,
            )
        except Exception as exc:
            print(f"  数据拉取失败: {exc}")
            continue

        pp = calculate_price_position(result.quotes, price_years)
        if pp is not None:
            print(f"  价格位置 3年: {pp:.1f}%")

        score = calculate_index_score(
            idx_info,
            result.valuation,
            pp,
            config.scoring,
            config.score_ranges,
        )
        scores.append(score)
        print(f"  综合打分: {score.total_score:.1f} ({score.label})")
        for f in score.factors:
            print(f"    {f.field}: {f.percentile:.1f}% → {f.score:.1f}")

    if not scores:
        print("\n无可用打分数据，退出。")
        sys.exit(1)

    print("\n正在生成 LLM 解读...")
    llm = None
    interpretations: dict[str, str] = {}
    try:
        llm = build_llm(config.llm)
        print("LLM 已连接")
    except Exception as exc:
        print(f"LLM 初始化失败: {exc}")

    if llm:
        for s in scores:
            if s.total_score <= 0:
                continue
            print(f"  解读: {s.name}...")
            interp = interpret_direct(llm, s)
            interpretations[s.code] = interp
            print(f"    → {interp[:60]}...")

    report = generate_report(
        scores,
        interpretations,
        sort_by=config.report.sort_by if config.report else "score",
    )

    filepath = export_report(report)
    print(f"\n报告已生成: {filepath}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="index-score",
        description="大盘指数量化打分工具",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="直接生成 Markdown 报告（不进入终端 UI）",
    )

    args = parser.parse_args()

    if args.report:
        _run_report()
    else:
        from index_score.ui.app import IndexScoreApp

        app = IndexScoreApp()
        app.run()


if __name__ == "__main__":
    main()
