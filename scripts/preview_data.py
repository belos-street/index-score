"""预览 AkShare 拉取的指数数据。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from index_score.config.loader import load_config
from index_score.config.models import IndexInfo
from index_score.data.fetcher import FetchError, fetch_price_history, fetch_valuation


def _separator(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _print_quote_table(quotes: list, last_n: int = 5) -> None:
    print(f"  {'date':<12} {'open':>10} {'high':>10} {'low':>10} {'close':>10} {'volume':>15}")
    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*15}")
    for q in quotes[-last_n:]:
        print(
            f"  {q.date:<12} {q.open:>10.2f} {q.high:>10.2f} "
            f"{q.low:>10.2f} {q.close:>10.2f} {q.volume:>15,.0f}"
        )


def _print_valuation(val: object) -> None:
    print(f"  date:                 {val.date}")
    print(f"  pe_ttm:               {val.pe_ttm}")
    print(f"  pe_percentile_5y:     {val.pe_percentile_5y}")
    print(f"  pb_lf:                {val.pb_lf}")
    print(f"  pb_percentile_5y:     {val.pb_percentile_5y}")
    print(f"  dividend_yield:       {val.dividend_yield}")
    print(f"  dividend_yield_pct5y: {val.dividend_yield_percentile_5y}")


def preview_index(index_info: IndexInfo) -> None:
    _separator(f"{index_info.name} ({index_info.code}) - {index_info.market}")

    try:
        quotes = fetch_price_history(index_info, years=3)
        print(f"\n  行情数据 (共 {len(quotes)} 条，最近 5 条):")
        _print_quote_table(quotes)
    except FetchError as exc:
        print(f"\n  行情数据拉取失败: {exc}")

    try:
        val = fetch_valuation(index_info)
        print(f"\n  估值数据 (最新):")
        _print_valuation(val)
    except FetchError as exc:
        print(f"\n  估值数据拉取失败: {exc}")


def main() -> None:
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    config = load_config(config_path)

    for idx in config.indexes:
        preview_index(idx)

    print()


if __name__ == "__main__":
    main()
