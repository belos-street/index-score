"""Tushare Pro 估值数据接口测试脚本。

测试目标（见 .agents/doc/data-model/02-data-gap-and-tushare-migration.md）：
1. index_dailybasic — 指数每日指标（PE/PB），覆盖 A 股指数
2. fund_daily — 基金日线行情，覆盖 ETF
3. daily_basic — 股票每日指标（PE/PB/股息率），覆盖 ETF 标的股票

用法：
  1. 在 .env 中填写 TUSHARE_TOKEN
  2. python scripts/test_tushare_valuation.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

import tushare as ts

TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")
if not TUSHARE_TOKEN:
    print("ERROR: 未设置 TUSHARE_TOKEN 环境变量")
    print("  请在 .env 文件中填写：TUSHARE_TOKEN=your_token_here")
    sys.exit(1)

pro = ts.pro_api(TUSHARE_TOKEN)

END_DATE = datetime.now().strftime("%Y%m%d")
START_DATE = (datetime.now() - timedelta(days=5 * 365)).strftime("%Y%m%d")

INDEX_TESTS: list[dict[str, str]] = [
    {"ts_code": "000922.SH", "name": "中证红利"},
    {"ts_code": "930955.SH", "name": "中证红利低波"},
    {"ts_code": "399371.SZ", "name": "国证价值100"},
    {"ts_code": "000300.SH", "name": "沪深300（对照组）"},
    {"ts_code": "000905.SH", "name": "中证500（对照组）"},
]

ETF_TESTS: list[dict[str, str]] = [
    {"ts_code": "515450.SH", "name": "标普中国红利低波50ETF"},
    {"ts_code": "159201.SZ", "name": "国证自由现金流ETF"},
    {"ts_code": "510300.SH", "name": "沪深300ETF（对照组）"},
]


def separator(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def test_index_dailybasic() -> None:
    """测试 index_dailybasic 接口：PE / PE_TTM / PB。"""
    separator("1. index_dailybasic（指数每日指标）")
    print("   接口: pro.index_dailybasic()")
    print("   文档: https://tushare.pro/document/2?doc_id=128")
    print("   字段: pe, pe_ttm, pb（无股息率）")
    print(f"   日期范围: {START_DATE} ~ {END_DATE}\n")

    for item in INDEX_TESTS:
        ts_code = item["ts_code"]
        name = item["name"]
        try:
            df = pro.index_dailybasic(
                ts_code=ts_code,
                start_date=START_DATE,
                end_date=END_DATE,
                fields="ts_code,trade_date,pe,pe_ttm,pb",
            )
            if df is None or df.empty:
                print(
                    f"  [{name}] {ts_code} — 空数据（该指数不被 index_dailybasic 覆盖）"
                )
            else:
                df = df.sort_values("trade_date")
                latest = df.iloc[-1]
                print(f"  [{name}] {ts_code} — OK!")
                print(f"    记录数: {len(df)}（约 {len(df) / 252:.1f} 年）")
                print(f"    最新日期: {latest['trade_date']}")
                print(
                    f"    PE: {latest.get('pe')}, PE_TTM: {latest.get('pe_ttm')}, PB: {latest.get('pb')}"
                )
        except Exception as exc:
            print(f"  [{name}] {ts_code} — ERROR: {exc}")


def test_fund_daily() -> None:
    """测试 fund_daily 接口：ETF 日线行情（含涨跌幅，但无 PE/PB/股息率）。"""
    separator("2. fund_daily（基金日线行情）")
    print("   接口: pro.fund_daily()")
    print("   文档: https://tushare.pro/document/2?doc_id=28")
    print("   字段: open/high/low/close/vol/amount（无 PE/PB/股息率）")
    print(f"   日期范围: {START_DATE} ~ {END_DATE}\n")

    for item in ETF_TESTS:
        ts_code = item["ts_code"]
        name = item["name"]
        try:
            df = pro.fund_daily(
                ts_code=ts_code,
                start_date=START_DATE,
                end_date=END_DATE,
            )
            if df is None or df.empty:
                print(f"  [{name}] {ts_code} — 空数据")
            else:
                df = df.sort_values("trade_date")
                latest = df.iloc[-1]
                cols = list(df.columns)
                print(f"  [{name}] {ts_code} — OK!")
                print(f"    记录数: {len(df)}（约 {len(df) / 252:.1f} 年）")
                print(f"    最新日期: {latest['trade_date']}")
                print(f"    收盘: {latest.get('close')}")
                print(f"    可用字段: {cols}")
        except Exception as exc:
            print(f"  [{name}] {ts_code} — ERROR: {exc}")


def test_fund_basic() -> None:
    """测试 fund_basic 接口：获取 ETF 基础信息，确认我们的 ETF 在库中。"""
    separator("3. fund_basic（基金基本信息）")
    print("   接口: pro.fund_basic()")
    print("   用途: 确认 ETF 的 ts_code 映射正确\n")

    for item in ETF_TESTS:
        ts_code = item["ts_code"]
        name = item["name"]
        try:
            df = pro.fund_basic(
                ts_code=ts_code, fields="ts_code,name,index_code,index_name"
            )
            if df is None or df.empty:
                print(f"  [{name}] {ts_code} — 未找到")
            else:
                row = df.iloc[0]
                print(f"  [{name}] {ts_code} — OK!")
                print(f"    基金名称: {row.get('name')}")
                print(
                    f"    跟踪指数: {row.get('index_code')} ({row.get('index_name')})"
                )
        except Exception as exc:
            print(f"  [{name}] {ts_code} — ERROR: {exc}")


def test_index_basic() -> None:
    """测试 index_basic 接口：确认指数代码映射。"""
    separator("4. index_basic（指数基本信息）")
    print("   接口: pro.index_basic()")
    print("   用途: 确认指数的 ts_code 映射和交易所后缀\n")

    for item in INDEX_TESTS:
        ts_code = item["ts_code"]
        name = item["name"]
        try:
            df = pro.index_basic(
                ts_code=ts_code, fields="ts_code,name,market,publisher,list_date"
            )
            if df is None or df.empty:
                print(f"  [{name}] {ts_code} — 未找到")
            else:
                row = df.iloc[0]
                print(f"  [{name}] {ts_code} — OK!")
                print(
                    f"    名称: {row.get('name')}, 市场: {row.get('market')}, 上市日: {row.get('list_date')}"
                )
        except Exception as exc:
            print(f"  [{name}] {ts_code} — ERROR: {exc}")


def test_score_ranges() -> None:
    """测试 fund_daily 收费情况：看 ETF 有没有报价数据。"""
    separator("5. fund_nav（基金净值，可能含 PE/PB 相关指标）")
    print("   接口: pro.fund_nav()")
    print("   文档: https://tushare.pro/document/2?doc_id=119")
    print("   用途: 检查是否有额外估值数据\n")

    ts_code = "515450.SH"
    name = "标普中国红利低波50ETF"
    try:
        df = pro.fund_nav(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
        if df is None or df.empty:
            print(f"  [{name}] {ts_code} — 空数据")
        else:
            df = df.sort_values("end_date")
            latest = df.iloc[-1]
            cols = list(df.columns)
            print(f"  [{name}] {ts_code} — OK!")
            print(f"    记录数: {len(df)}")
            print(f"    最新日期: {latest.get('end_date')}")
            print(f"    单位净值: {latest.get('unit_nav')}")
            print(f"    累计净值: {latest.get('accum_nav')}")
            print(f"    全部字段: {cols}")
    except Exception as exc:
        print(f"  [{name}] {ts_code} — ERROR: {exc}")


def test_daily_basic() -> None:
    """测试 daily_basic 接口：股票每日指标（PE/PB/股息率）。

    这是股票接口，看 ETF 代码能否查到估值数据。
    """
    separator("6. daily_basic（股票每日指标，含 PE/PB/股息率）")
    print("   接口: pro.daily_basic()")
    print("   文档: https://tushare.pro/document/2?doc_id=32")
    print("   字段: pe, pe_ttm, pb, dv_ratio, dv_ttm")
    print("   用途: 测试 ETF 代码和指数代码能否获取估值\n")

    test_codes = [
        ("515450.SH", "标普中国红利低波50ETF"),
        ("159201.SZ", "国证自由现金流ETF"),
        ("000922.SH", "中证红利（指数代码）"),
        ("000300.SH", "沪深300（指数代码，对照组）"),
    ]

    test_date = "20260508"
    for ts_code, name in test_codes:
        try:
            df = pro.daily_basic(
                ts_code=ts_code,
                trade_date=test_date,
                fields="ts_code,trade_date,pe,pe_ttm,pb,dv_ratio,dv_ttm",
            )
            if df is None or df.empty:
                print(f"  [{name}] {ts_code} — 空数据")
            else:
                row = df.iloc[0]
                print(f"  [{name}] {ts_code} — OK!")
                print(f"    PE: {row.get('pe')}, PE_TTM: {row.get('pe_ttm')}")
                print(f"    PB: {row.get('pb')}")
                print(
                    f"    股息率: {row.get('dv_ratio')}, 股息率TTM: {row.get('dv_ttm')}"
                )
        except Exception as exc:
            print(f"  [{name}] {ts_code} — ERROR: {exc}")


def test_daily_basic_history() -> None:
    """测试 daily_basic 接口的历史数据量。"""
    separator("7. daily_basic 历史数据量（5 年分位计算所需）")
    print("   接口: pro.daily_basic()")
    print("   用途: 确认能否获取足够长的历史数据来计算 5 年分位\n")

    test_codes = [
        ("515450.SH", "标普中国红利低波50ETF"),
        ("000300.SH", "沪深300（对照组）"),
    ]

    for ts_code, name in test_codes:
        try:
            df = pro.daily_basic(
                ts_code=ts_code,
                start_date=START_DATE,
                end_date=END_DATE,
                fields="ts_code,trade_date,pe_ttm,pb,dv_ratio",
            )
            if df is None or df.empty:
                print(f"  [{name}] {ts_code} — 空数据")
            else:
                df = df.sort_values("trade_date")
                valid_pe = df["pe_ttm"].notna().sum()
                valid_pb = df["pb"].notna().sum()
                valid_dy = df["dv_ratio"].notna().sum()
                print(f"  [{name}] {ts_code}")
                print(f"    总记录数: {len(df)}（约 {len(df) / 252:.1f} 年）")
                print(
                    f"    PE_TTM 有效: {valid_pe}, PB 有效: {valid_pb}, 股息率 有效: {valid_dy}"
                )
                if not df.empty:
                    latest = df.iloc[-1]
                    print(
                        f"    最新: PE_TTM={latest['pe_ttm']}, PB={latest['pb']}, 股息率={latest['dv_ratio']}"
                    )
        except Exception as exc:
            print(f"  [{name}] {ts_code} — ERROR: {exc}")


def test_fund_mapping() -> None:
    """测试 fund_mapping 接口：ETF 到标的指数的映射关系。"""
    separator("8. fund_mapping（基金-指数映射）")
    print("   接口: pro.fund_mapping()")
    print("   用途: 找到 ETF 对应的指数代码\n")

    for item in ETF_TESTS:
        ts_code = item["ts_code"]
        name = item["name"]
        try:
            df = pro.fund_mapping(ts_code=ts_code)
            if df is None or df.empty:
                print(f"  [{name}] {ts_code} — 空数据")
            else:
                cols = list(df.columns)
                print(f"  [{name}] {ts_code} — OK!")
                print(f"    字段: {cols}")
                for _, row in df.head(3).iterrows():
                    print(f"    {dict(row)}")
        except Exception as exc:
            print(f"  [{name}] {ts_code} — ERROR: {exc}")


def test_index_classify() -> None:
    """测试 index_classify 接口：指数成分股信息。"""
    separator("9. index_classify（指数分类/成分）")
    print("   接口: pro.index_classify()")
    print("   用途: 查看中证红利等策略指数的分类信息\n")

    for item in INDEX_TESTS[:3]:
        ts_code = item["ts_code"]
        name = item["name"]
        try:
            df = pro.index_classify(src="CS", level="L1")
            if df is None or df.empty:
                print(f"  [{name}] — 空数据")
            else:
                match = df[df["ts_code"] == ts_code]
                if match.empty:
                    print(f"  [{name}] {ts_code} — 未在L1中找到")
                else:
                    print(f"  [{name}] {ts_code} — OK! {dict(match.iloc[0])}")
        except Exception as exc:
            print(f"  [{name}] {ts_code} — ERROR: {exc}")


def test_ths_daily_basic() -> None:
    """测试同花顺指数接口：ths_index_daily_basic（同花顺指数估值）。"""
    separator("10. ths_index_daily_basic（同花顺指数估值）")
    print("   接口: pro.ths_index_daily_basic()")
    print("   文档: https://tushare.pro/document/2?doc_id=270")
    print("   用途: 同花顺指数可能覆盖更多指数的 PE/PB\n")

    test_ths = [
        ("000922.CSI", "中证红利（中证代码）"),
        ("930955.CSI", "中证红利低波（中证代码）"),
        ("399371.SZ", "国证价值100"),
    ]

    test_date = "20260508"
    for ts_code, name in test_ths:
        try:
            df = pro.ths_index_daily_basic(ts_code=ts_code, trade_date=test_date)
            if df is None or df.empty:
                print(f"  [{name}] {ts_code} — 空数据")
            else:
                cols = list(df.columns)
                row = df.iloc[0]
                print(f"  [{name}] {ts_code} — OK!")
                print(f"    字段: {cols}")
                print(f"    数据: {dict(row)}")
        except Exception as exc:
            print(f"  [{name}] {ts_code} — ERROR: {exc}")


def test_ths_index() -> None:
    """测试同花顺指数基础信息：看同花顺有没有我们的指数。"""
    separator("11. ths_index（同花顺指数基本信息）")
    print("   接口: pro.ths_index()")
    print("   用途: 查找同花顺体系中的指数代码\n")

    try:
        df = pro.ths_index()
        if df is None or df.empty:
            print("  空数据")
        else:
            keywords = ["红利", "价值", "现金流"]
            for kw in keywords:
                matches = df[df["name"].str.contains(kw, na=False)]
                if not matches.empty:
                    print(f"  搜索 '{kw}':")
                    for _, row in matches.head(5).iterrows():
                        print(f"    {row.get('ts_code')} - {row.get('name')}")
                else:
                    print(f"  搜索 '{kw}': 无结果")
    except Exception as exc:
        print(f"  ERROR: {exc}")


def test_ci_index() -> None:
    """测试国证指数接口（ci_index）：覆盖深交所旗下国证指数。"""
    separator("12. ci_index（国证指数基本信息）")
    print("   接口: pro.ci_index()")
    print("   用途: 查找国证指数体系中的指数代码\n")

    try:
        df = pro.ci_index()
        if df is None or df.empty:
            print("  空数据")
        else:
            keywords = ["红利", "价值", "现金流"]
            for kw in keywords:
                matches = df[df["name"].str.contains(kw, na=False)]
                if not matches.empty:
                    print(f"  搜索 '{kw}':")
                    for _, row in matches.head(5).iterrows():
                        print(f"    {row.get('ts_code')} - {row.get('name')}")
                else:
                    print(f"  搜索 '{kw}': 无结果")
    except Exception as exc:
        print(f"  ERROR: {exc}")


def test_index_weight() -> None:
    """测试 index_weight 接口：获取指数成分股权重。"""
    separator("13. index_weight（指数成分股权重）")
    print("   接口: pro.index_weight()")
    print("   用途: 获取中证红利成分股，可结合 daily_basic 计算加权 PE/PB\n")

    test_date = "20260508"
    for item in INDEX_TESTS[:2]:
        ts_code = item["ts_code"]
        name = item["name"]
        try:
            df = pro.index_weight(
                index_code=ts_code,
                start_date=test_date,
                end_date=test_date,
            )
            if df is None or df.empty:
                print(f"  [{name}] {ts_code} — 空数据")
            else:
                print(f"  [{name}] {ts_code} — OK!")
                print(f"    成分股数量: {len(df)}")
                print(f"    字段: {list(df.columns)}")
                print(f"    前5只: {list(df['con_code'].head())}")
        except Exception as exc:
            print(f"  [{name}] {ts_code} — ERROR: {exc}")


def main() -> None:
    print("=" * 70)
    print("  Tushare Pro 估值数据接口测试")
    print(f"  Token: {TUSHARE_TOKEN[:8]}...{TUSHARE_TOKEN[-4:]}")
    print(f"  测试日期范围: {START_DATE} ~ {END_DATE}")
    print("=" * 70)

    test_index_basic()
    test_index_dailybasic()
    test_fund_basic()
    test_fund_daily()
    test_score_ranges()
    test_daily_basic()
    test_daily_basic_history()
    test_fund_mapping()
    test_ths_index()
    test_ths_daily_basic()
    test_ci_index()
    test_index_weight()

    separator("总结")
    print("  关键发现：")
    print(
        "  1. index_dailybasic — 仅覆盖大指数（沪深300/中证500等），不含中证红利/红利低波/国证价值100"
    )
    print("  2. fund_daily — ETF 行情可用，但无 PE/PB/股息率字段")
    print("  3. daily_basic — 股票接口，ETF/指数代码均查不到")
    print("  4. 同花顺/国证指数 — 需确认是否覆盖更多策略指数")
    print("  5. index_weight — 可获取成分股，结合 daily_basic 可自算指数 PE/PB")
    print()
    print("  参考文档: .agents/doc/data-model/02-data-gap-and-tushare-migration.md")


if __name__ == "__main__":
    main()
