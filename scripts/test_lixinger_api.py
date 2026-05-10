"""测试理杏仁 Open API 连通性和数据可用性。

理杏仁 API 关键点：
  - 指数信息: POST /api/cn/index
  - 指数基本面: POST /api/cn/index/fundamental
  - metricsList 格式: [metricsName].[granularity].[metricsType].[statisticsDataType]
    - metricsName: pe_ttm, pb, ps_ttm, dyr, cp, r_cp, mc 等
    - granularity: fs(上市以来), y20, y10, y5, y3, y1
    - metricsType: mcw(市值加权), ew(等权), ewpvo, avg, median
    - statisticsDataType: cv(当前值), cvpos(分位点%), q5v, q8v, q2v, minv, maxv, avgv

用法：
  python scripts/test_lixinger_api.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TOKEN = os.getenv("LIXINGER_TOKEN", "")
BASE = "https://open.lixinger.com/api"

TARGET_INDEXES = {
    "930955": "红利低波100",
    "399967": "中证军工",
    "000015": "红利指数",
    "000300": "沪深300",
    "000905": "中证500",
}


def post(path: str, body: dict, timeout: int = 30):
    url = f"{BASE}{path}"
    body["token"] = TOKEN
    resp = requests.post(url, json=body, timeout=timeout)
    if resp.status_code != 200:
        print(f"  ⚠️ HTTP {resp.status_code}: {resp.text[:500]}")
        return None
    result = resp.json()
    if isinstance(result, dict) and "data" in result:
        if result.get("code") != 1:
            print(
                f"  ⚠️ API 业务错误: code={result.get('code')}, message={result.get('message')}"
            )
        return result["data"]
    return result


def fmt(v, pct=False):
    if v is None or v == "N/A":
        return "N/A"
    try:
        fv = float(v)
        return f"{fv * 100:.1f}%" if pct else f"{fv:.2f}"
    except (ValueError, TypeError):
        return str(v)


def test_1_index_info():
    print("=" * 60)
    print("  测试1: 查询指数基本信息 (POST /api/cn/index)")
    print("=" * 60)

    codes = list(TARGET_INDEXES.keys())
    data = post("/cn/index", {"stockCodes": codes})

    if not isinstance(data, list):
        print(f"  ⚠️ 返回格式异常: {type(data)}")
        print(f"  {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
        return []

    found = []
    for item in data:
        code = item.get("stockCode", "")
        name = item.get("name", "")
        series = item.get("series", "")
        calc = item.get("calculationMethod", "")
        src = item.get("source", "")
        launch = item.get("launchDate", "")
        print(
            f"  ✅ {code} | {name} | 系列={series} | 加权={calc} | 来源={src} | 发布={launch}"
        )
        found.append(item)

    missing = set(codes) - {item.get("stockCode") for item in found}
    for m in missing:
        print(f"  ❌ {m} ({TARGET_INDEXES.get(m, '?')}) 未找到")

    return found


def test_2_single_index():
    print(f"\n{'=' * 60}")
    print("  测试2: 单指数最新估值 (POST /api/cn/index/fundamental)")
    print("=" * 60)

    code = "930955"
    metrics = [
        "cp",
        "r_cp",
        "mc",
        "pe_ttm.mcw",
        "pb.mcw",
        "dyr.mcw",
        "pe_ttm.y5.mcw.cvpos",
        "pb.y5.mcw.cvpos",
        "dyr.y5.mcw.cvpos",
    ]

    data = post(
        "/cn/index/fundamental",
        {
            "stockCodes": [code],
            "date": "2026-05-08",
            "metricsList": metrics,
        },
    )

    if data is None:
        return

    if isinstance(data, list) and len(data) > 0:
        item = data[0]
        print(f"\n  指数: {code} ({TARGET_INDEXES.get(code, '?')})")
        print(f"  返回字段 ({len(item)} 个):")
        for k, v in sorted(item.items()):
            if v is not None and v != "":
                print(f"    {k}: {v}")
    else:
        print(f"  返回: {json.dumps(data, ensure_ascii=False)[:500]}")


def test_3_percentile_detail():
    print(f"\n{'=' * 60}")
    print("  测试3: 分位点详细统计（5年窗口）")
    print("=" * 60)

    code = "930955"
    metrics = [
        "pe_ttm.y5.mcw.cv",
        "pe_ttm.y5.mcw.cvpos",
        "pe_ttm.y5.mcw.minv",
        "pe_ttm.y5.mcw.maxv",
        "pe_ttm.y5.mcw.q2v",
        "pe_ttm.y5.mcw.q5v",
        "pe_ttm.y5.mcw.q8v",
        "pe_ttm.y5.mcw.avgv",
        "pb.y5.mcw.cv",
        "pb.y5.mcw.cvpos",
        "pb.y5.mcw.minv",
        "pb.y5.mcw.maxv",
        "pb.y5.mcw.q2v",
        "pb.y5.mcw.q5v",
        "pb.y5.mcw.q8v",
        "pb.y5.mcw.avgv",
        "dyr.y5.mcw.cv",
        "dyr.y5.mcw.cvpos",
        "dyr.y5.mcw.minv",
        "dyr.y5.mcw.maxv",
        "dyr.y5.mcw.q2v",
        "dyr.y5.mcw.q5v",
        "dyr.y5.mcw.q8v",
        "dyr.y5.mcw.avgv",
    ]

    data = post(
        "/cn/index/fundamental",
        {
            "stockCodes": [code],
            "date": "2026-05-08",
            "metricsList": metrics,
        },
    )

    if data is None:
        return

    if isinstance(data, list) and len(data) > 0:
        item = data[0]
        print(f"\n  指数: {code} ({TARGET_INDEXES.get(code, '?')})\n")
        for mname, label in [("pe_ttm", "PE-TTM"), ("pb", "PB"), ("dyr", "股息率")]:
            cv = item.get(f"{mname}.y5.mcw.cv")
            pos = item.get(f"{mname}.y5.mcw.cvpos")
            lo = item.get(f"{mname}.y5.mcw.minv")
            hi = item.get(f"{mname}.y5.mcw.maxv")
            q2 = item.get(f"{mname}.y5.mcw.q2v")
            q5 = item.get(f"{mname}.y5.mcw.q5v")
            q8 = item.get(f"{mname}.y5.mcw.q8v")
            avg = item.get(f"{mname}.y5.mcw.avgv")
            print(f"  {label} (5年, 市值加权):")
            print(f"    当前值: {cv}  |  分位点: {pos}")
            print(f"    最小值: {lo}  |  最大值: {hi}")
            print(f"    20%分位: {q2} |  50%分位: {q5} |  80%分位: {q8}")
            print(f"    平均值: {avg}")
            print()
    else:
        print(f"  返回: {json.dumps(data, ensure_ascii=False)[:500]}")


def test_4_history_range():
    print(f"\n{'=' * 60}")
    print("  测试4: 指数历史数据（时间范围, limit=5）")
    print("=" * 60)

    code = "930955"
    metrics = [
        "cp",
        "pe_ttm.mcw",
        "pb.mcw",
        "dyr.mcw",
        "pe_ttm.y5.mcw.cvpos",
        "pb.y5.mcw.cvpos",
        "dyr.y5.mcw.cvpos",
    ]

    data = post(
        "/cn/index/fundamental",
        {
            "stockCodes": [code],
            "startDate": "2024-01-01",
            "endDate": "2026-05-08",
            "metricsList": metrics,
            "limit": 5,
        },
    )

    if data is None:
        return

    if isinstance(data, list):
        print(f"\n  返回 {len(data)} 条记录:")
        for i, item in enumerate(data):
            d = item.get("date", "?")
            cp = item.get("cp", "N/A")
            pe = item.get("pe_ttm.mcw", "N/A")
            pb = item.get("pb.mcw", "N/A")
            dyr = item.get("dyr.mcw", "N/A")
            pe_p = item.get("pe_ttm.y5.mcw.cvpos", "N/A")
            pb_p = item.get("pb.y5.mcw.cvpos", "N/A")
            dyr_p = item.get("dyr.y5.mcw.cvpos", "N/A")
            print(
                f"  [{i + 1}] {d} | 收盘={cp} | PE={fmt(pe)} | PB={fmt(pb)} | 股息率={fmt(dyr, True)}"
            )
            print(
                f"       PE分位={fmt(pe_p, True)} | PB分位={fmt(pb_p, True)} | 股息率分位={fmt(dyr_p, True)}"
            )
    else:
        print(f"  返回: {json.dumps(data, ensure_ascii=False)[:500]}")


def test_5_multi_index():
    print(f"\n{'=' * 60}")
    print("  测试5: 批量查询多个指数估值")
    print("=" * 60)

    codes = list(TARGET_INDEXES.keys())
    metrics = [
        "cp",
        "pe_ttm.mcw",
        "pb.mcw",
        "dyr.mcw",
        "pe_ttm.y5.mcw.cvpos",
        "pb.y5.mcw.cvpos",
        "dyr.y5.mcw.cvpos",
    ]

    data = post(
        "/cn/index/fundamental",
        {
            "stockCodes": codes,
            "date": "2026-05-08",
            "metricsList": metrics,
        },
    )

    if data is None:
        return

    if isinstance(data, list):
        print(f"\n  返回 {len(data)} 条记录:\n")
        print(
            f"  {'代码':<10} {'名称':<14} {'收盘':>10} {'PE':>8} {'PB':>6} {'股息率':>6} {'PE分位':>8} {'PB分位':>8} {'股息率分位':>10}"
        )
        print(f"  {'-' * 90}")
        for item in data:
            code = item.get("stockCode", "?")
            name = TARGET_INDEXES.get(code, "?")
            cp = item.get("cp", "N/A")
            pe = item.get("pe_ttm.mcw", "N/A")
            pb_v = item.get("pb.mcw", "N/A")
            dyr = item.get("dyr.mcw", "N/A")
            pe_p = item.get("pe_ttm.y5.mcw.cvpos", "N/A")
            pb_p = item.get("pb.y5.mcw.cvpos", "N/A")
            dyr_p = item.get("dyr.y5.mcw.cvpos", "N/A")
            print(
                f"  {code:<10} {name:<14} {fmt(cp):>10} {fmt(pe):>8} {fmt(pb_v):>6} "
                f"{fmt(dyr, True):>6} {fmt(pe_p, True):>8} {fmt(pb_p, True):>8} {fmt(dyr_p, True):>10}"
            )
    else:
        print(f"  返回: {json.dumps(data, ensure_ascii=False)[:500]}")


def main() -> None:
    print("=" * 60)
    print("  理杏仁 Open API 连通性测试")
    print("=" * 60)
    print(
        f"  Token: {TOKEN[:8]}...{TOKEN[-4:]}"
        if len(TOKEN) > 12
        else f"  Token: {TOKEN}"
    )
    print()

    if not TOKEN:
        print("  ❌ LIXINGER_TOKEN 未设置，请在 .env 中配置")
        sys.exit(1)

    for name, func in [
        ("test_1", test_1_index_info),
        ("test_2", test_2_single_index),
        ("test_3", test_3_percentile_detail),
        ("test_4", test_4_history_range),
        ("test_5", test_5_multi_index),
    ]:
        try:
            func()
        except Exception as e:
            print(f"  ❌ {name} 失败: {e}")

    print(f"\n{'=' * 60}")
    print("  测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
