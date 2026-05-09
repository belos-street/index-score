"""测试 ETF 代码是否能替代指数代码拉取行情和估值数据。"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import akshare as ak
import pandas as pd

pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 200)

ETFS = [
    ("SPCLLHCP", "标普中国红利低波50", "sh515450"),
    ("980092", "国证自由现金流", "sz159201"),
]

QUOTE_APIS = {
    "stock_zh_index_daily_tx": {
        "func": ak.stock_zh_index_daily_tx,
        "label": "腾讯",
    },
    "stock_zh_index_daily": {
        "func": ak.stock_zh_index_daily,
        "label": "新浪",
    },
    "stock_zh_a_daily": {
        "func": ak.stock_zh_a_daily,
        "label": "A股日线",
        "kwargs": {"start_date": "20230101", "end_date": "22220101"},
    },
}


def test_etf(idx_code: str, idx_name: str, etf_code: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {idx_name} ({idx_code})  ->  ETF: {etf_code}")
    print(f"{'=' * 70}")

    print("\n  --- 行情接口 ---")
    for api_name, api_info in QUOTE_APIS.items():
        try:
            kwargs = api_info.get("kwargs", {})
            df = api_info["func"](symbol=etf_code, **kwargs)
            if df is None or df.empty:
                print(f"    [{api_info['label']}] {api_name}  =>  空数据")
            else:
                last = df.iloc[-1]
                print(
                    f"    [{api_info['label']}] {api_name}  =>  {len(df)} 条, 最新: {last.to_dict()}"
                )
        except Exception as e:
            print(
                f"    [{api_info['label']}] {api_name}  =>  失败: {type(e).__name__}: {e}"
            )
        time.sleep(0.3)

    print("\n  --- 估值接口 ---")
    try:
        df = ak.stock_zh_index_value_csindex(symbol=idx_code)
        print(f"    [中证估值 index={idx_code}]  =>  {len(df)} 条")
        if not df.empty:
            print(f"      最新: {df.iloc[-1].to_dict()}")
    except Exception as e:
        print(f"    [中证估值 index={idx_code}]  =>  失败: {type(e).__name__}: {e}")

    try:
        df = ak.stock_zh_index_value_csindex(symbol=etf_code)
        print(f"    [中证估值 etf={etf_code}]  =>  {len(df)} 条")
        if not df.empty:
            print(f"      最新: {df.iloc[-1].to_dict()}")
    except Exception as e:
        print(f"    [中证估值 etf={etf_code}]  =>  失败: {type(e).__name__}: {e}")


def main() -> None:
    for idx_code, idx_name, etf_code in ETFS:
        test_etf(idx_code, idx_name, etf_code)

    print(f"\n{'=' * 70}")
    print("  测试完成")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
