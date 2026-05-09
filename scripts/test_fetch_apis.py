"""逐个测试 AkShare 指数接口，找出每个指数最优的数据源。

用法: python scripts/test_fetch_apis.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import akshare as ak
import pandas as pd

from index_score.config.loader import load_config

pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 15)


A_SHARE_QUOTE_APIS = {
    "stock_zh_index_daily (新浪)": {
        "func": ak.stock_zh_index_daily,
        "symbol_fn": lambda code: f"sz{code}" if code.startswith("3") else f"sh{code}",
    },
    "stock_zh_index_daily_tx (腾讯)": {
        "func": ak.stock_zh_index_daily_tx,
        "symbol_fn": lambda code: f"sz{code}" if code.startswith("3") else f"sh{code}",
    },
    "stock_zh_index_daily_em (东方财富)": {
        "func": ak.stock_zh_index_daily_em,
        "symbol_fn": lambda code: f"sz{code}" if code.startswith("3") else f"sh{code}",
    },
    "index_zh_a_hist (东方财富通用)": {
        "func": ak.index_zh_a_hist,
        "symbol_fn": lambda code: code,
        "kwargs": {"period": "daily", "start_date": "20230101", "end_date": "22220101"},
    },
}

US_QUOTE_APIS = {
    "index_us_stock_sina (新浪)": {
        "func": ak.index_us_stock_sina,
        "symbol_fn": lambda code: {
            "IXIC": ".IXIC",
            "SPX": ".INX",
            "DJI": ".DJI",
            "NDX": ".NDX",
        }.get(code, f".{code}"),
    },
}

VALUATION_APIS = {
    "stock_zh_index_value_csindex (中证估值)": {
        "func": ak.stock_zh_index_value_csindex,
        "symbol_fn": lambda code: code,
    },
}


def _try_api(name: str, func, symbol: str, kwargs: dict | None = None) -> None:
    kwargs = kwargs or {}
    try:
        df = func(symbol=symbol, **kwargs)
        if df is None or df.empty:
            print(f"    [{name}] symbol={symbol}  =>  空数据")
            return
        cols = df.columns.tolist()
        rows = len(df)
        last = df.iloc[-1]
        print(f"    [{name}] symbol={symbol}  =>  {rows} 条, 列={cols}")
        print(f"      最新: {last.to_dict()}")
    except Exception as exc:
        print(f"    [{name}] symbol={symbol}  =>  失败: {type(exc).__name__}: {exc}")


def test_index(code: str, name: str, market: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {name} ({code})  market={market}")
    print(f"{'=' * 70}")

    if market == "CN":
        print("\n  --- 行情接口 ---")
        for api_name, api_info in A_SHARE_QUOTE_APIS.items():
            symbol = api_info["symbol_fn"](code)
            kwargs = api_info.get("kwargs", {})
            _try_api(api_name, api_info["func"], symbol, kwargs)
            time.sleep(0.5)

        print("\n  --- 估值接口 ---")
        for api_name, api_info in VALUATION_APIS.items():
            symbol = api_info["symbol_fn"](code)
            _try_api(api_name, api_info["func"], symbol)
            time.sleep(0.5)

    elif market == "US":
        print("\n  --- 行情接口 ---")
        for api_name, api_info in US_QUOTE_APIS.items():
            symbol = api_info["symbol_fn"](code)
            _try_api(api_name, api_info["func"], symbol)
            time.sleep(0.5)

        print("\n  --- 估值接口 ---")
        print("    (美股无 AkShare 估值接口)")


def main() -> None:
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    config = load_config(config_path)

    for idx in config.indexes:
        test_index(idx.code, idx.name, idx.market)

    print(f"\n{'=' * 70}")
    print("  测试完成")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
