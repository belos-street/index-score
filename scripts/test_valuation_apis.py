"""测试中证红利 000922：行情 + PE/PB/股息率数据获取。

基于用户提供的代码改造，替换已移除的接口：
- ak.index_value_hist_funddb => 已被 AkShare 移除，不可用
- ak.stock_zh_index_hist_csindex => 行情+PE 一体，5年历史，可用
- ak.stock_index_pe_lg => 理杏仁 PE，中文名查询
- ak.stock_index_pb_lg => 理杏仁 PB，中文名查询
- ak.stock_zh_index_value_csindex => csindex PE+股息率，仅20条
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import akshare as ak
import pandas as pd

pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 10)

INDEX_CODE = "000922"
INDEX_NAME = "中证红利"
TODAY = datetime.now()
START_QUOTE = (TODAY - timedelta(days=3 * 365)).strftime("%Y%m%d")
START_VALUATION = TODAY - timedelta(days=5 * 365)
END_DATE = TODAY.strftime("%Y%m%d")

print("=" * 60)
print(f"正在获取：【{INDEX_NAME} {INDEX_CODE}】数据")
print("=" * 60)

# ================================================================
# 1. 行情 + PE（stock_zh_index_hist_csindex，一体接口）
# ================================================================
print("\n1. 正在获取 3年行情+PE数据 (stock_zh_index_hist_csindex)...")
try:
    df = ak.stock_zh_index_hist_csindex(
        symbol=INDEX_CODE,
        start_date=START_QUOTE,
        end_date=END_DATE,
    )
    index_quote = df[
        ["日期", "收盘", "开盘", "最高", "最低", "涨跌幅", "滚动市盈率"]
    ].copy()
    index_quote["日期"] = pd.to_datetime(index_quote["日期"])
    index_quote = index_quote.rename(columns={"滚动市盈率": "PE"})
    print(f"  ✅ 行情+PE 数据获取完成：共 {len(index_quote)} 条")
    print(f"  日期范围: {index_quote['日期'].min()} ~ {index_quote['日期'].max()}")
    print(f"  PE 范围: {index_quote['PE'].min()} ~ {index_quote['PE'].max()}")
    print("  最新 5 条:")
    print(index_quote.tail(5).to_string(index=False))
except Exception as e:
    print(f"  ❌ 行情+PE 获取失败：{e}")
    index_quote = pd.DataFrame()

# ================================================================
# 2. PB（理杏仁 stock_index_pb_lg）
# ================================================================
print("\n2. 正在获取 PB 数据 (stock_index_pb_lg, 理杏仁)...")
pb_df = pd.DataFrame()
try:
    pb_df = ak.stock_index_pb_lg(symbol=INDEX_NAME)
    pb_df["日期"] = pd.to_datetime(pb_df["日期"])
    pb_df = pb_df[["日期", "市净率"]].rename(columns={"市净率": "PB"})
    pb_df = pb_df[pb_df["日期"] >= pd.to_datetime(START_VALUATION.strftime("%Y%m%d"))]
    print(f"  ✅ PB 数据获取完成：共 {len(pb_df)} 条")
    print(f"  PB 范围: {pb_df['PB'].min()} ~ {pb_df['PB'].max()}")
    print("  最新 5 条:")
    print(pb_df.tail(5).to_string(index=False))
except KeyError:
    print(f"  ❌ PB 获取失败：理杏仁不支持 [{INDEX_NAME}]（KeyError）")
except Exception as e:
    print(f"  ❌ PB 获取失败：{type(e).__name__}: {e}")

# ================================================================
# 3. PE + 股息率（csindex stock_zh_index_value_csindex，仅20条）
# ================================================================
print("\n3. 正在获取 PE+股息率 (stock_zh_index_value_csindex, csindex实时)...")
try:
    val_df = ak.stock_zh_index_value_csindex(symbol=INDEX_CODE)
    val_df["日期"] = pd.to_datetime(val_df["日期"])
    val_df = val_df.sort_values("日期")
    print(f"  ✅ PE+股息率 获取完成：共 {len(val_df)} 条（注意：仅最近20条）")
    print(f"  列: {val_df.columns.tolist()}")
    print("  最新 5 条:")
    print(val_df.tail(5).to_string(index=False))
except Exception as e:
    print(f"  ❌ PE+股息率 获取失败：{e}")

# ================================================================
# 4. 合并行情+PE 与 PB（5年估值）
# ================================================================
if not index_quote.empty:
    print("\n4. 合并行情+PE 与 PB...")
    final_df = index_quote.copy()
    if not pb_df.empty:
        final_df = pd.merge(final_df, pb_df, on="日期", how="left")
        pb_coverage = final_df["PB"].notna().sum()
        print(f"  PB 匹配到 {pb_coverage}/{len(final_df)} 条")
    else:
        final_df["PB"] = None
        print("  ⚠️ PB 无数据，已跳过")

    final_df["股息率"] = None
    print("  ⚠️ 股息率 5年历史暂无数据源，已跳过")

    final_df = final_df.sort_values("日期").reset_index(drop=True)

    # ================================================================
    # 5. 输出最终结果
    # ================================================================
    print("\n" + "=" * 60)
    print("📊 最终数据集（最后 10 行）：")
    print("=" * 60)
    print(final_df.tail(10).to_string(index=False))

    print(f"\n📈 总数据量：{len(final_df)} 行")
    print(f"  字段：{final_df.columns.tolist()}")
    print(f"  PE 覆盖率：{final_df['PE'].notna().sum()}/{len(final_df)}")
    print(f"  PB 覆盖率：{final_df['PB'].notna().sum()}/{len(final_df)}")
    print(f"  股息率覆盖率：{final_df['股息率'].notna().sum()}/{len(final_df)}")

# ================================================================
# 6. 接口可用性总结
# ================================================================
print("\n" + "=" * 60)
print("🔍 接口可用性总结")
print("=" * 60)
print(
    f"  stock_zh_index_hist_csindex (行情+PE): {'✅ 可用' if not index_quote.empty else '❌ 不可用'}"
)
print(
    f"  stock_index_pb_lg (理杏仁 PB):         {'✅ 可用' if not pb_df.empty else '❌ 不可用'}"
)
print("  stock_zh_index_value_csindex (PE+股息率): ⚠️ 仅20条快照，无法做5年分位数")
print("  index_value_hist_funddb (韭圈儿 PE/PB/股息率): ❌ 已从AkShare移除")
