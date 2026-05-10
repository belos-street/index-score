"""通过 Tushare Pro MCP 服务测试上证指数数据。

用上证指数 (000001.SH) 作为标准，测试哪些数据可以拿到。

认证方式: Authorization: Bearer {token}

用法：
  python scripts/test_tushare_index.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

import requests

TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")
if not TUSHARE_TOKEN:
    print("ERROR: 未设置 TUSHARE_TOKEN 环境变量")
    sys.exit(1)

MCP_URL = f"https://api.tushare.pro/mcp/token={TUSHARE_TOKEN}"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": f"Bearer {TUSHARE_TOKEN}",
}
REQ_ID = 0


def mcp_call(method: str, params: dict | None = None) -> dict | None:
    global REQ_ID
    REQ_ID += 1
    body: dict = {"jsonrpc": "2.0", "id": REQ_ID, "method": method}
    if params is not None:
        body["params"] = params
    resp = requests.post(MCP_URL, headers=HEADERS, json=body, timeout=30)
    content_type = resp.headers.get("content-type", "")
    raw = resp.content.decode("utf-8", errors="replace")
    if "text/event-stream" in content_type:
        data_lines = [l[6:] for l in raw.split("\n") if l.startswith("data: ")]
        if data_lines:
            return json.loads(data_lines[-1])
    if "application/json" in content_type:
        return json.loads(raw)
    return {"raw": raw[:1000]}


def call_tool(name: str, args: dict, label: str = "") -> dict:
    """调用 MCP 工具，返回解析后的数据列表"""
    r = mcp_call("tools/call", {"name": name, "arguments": args})
    content = (r or {}).get("result", {}).get("content", [])
    is_error = (r or {}).get("result", {}).get("isError", False)

    if content:
        text = content[0].get("text", "")
        try:
            data = json.loads(text)
            return {"success": True, "data": data, "count": len(data) if isinstance(data, list) else 1}
        except (json.JSONDecodeError, TypeError):
            return {"success": False, "error": text[:200]}
    elif is_error:
        return {"success": False, "error": str(r)[:200]}
    return {"success": False, "error": "无返回"}


def main() -> None:
    index_code = "000001.SH"
    print(f"测试标的：上证指数 ({index_code})")
    print(f"Token: {TUSHARE_TOKEN[:8]}...{TUSHARE_TOKEN[-4:]}")
    print()

    mcp_call("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "tushare-test", "version": "1.0.0"},
    })

    results = {}

    print("=" * 70)
    print("  1. index_basic — 指数基本信息")
    print("=" * 70)
    r = call_tool("index_basic", {"ts_code": index_code})
    if r["success"]:
        print(f"  OK! 记录数: {r['count']}")
        if isinstance(r["data"], list):
            for row in r["data"][:3]:
                print(f"    {row}")
    else:
        print(f"  FAIL: {r['error']}")
    results["index_basic"] = r

    print("\n" + "=" * 70)
    print("  2. index_daily — 指数日线行情 (近3日)")
    print("=" * 70)
    r = call_tool("index_daily", {"ts_code": index_code, "start_date": "20260506", "end_date": "20260508"})
    if r["success"]:
        print(f"  OK! 记录数: {r['count']}")
        if isinstance(r["data"], list):
            for row in r["data"][:5]:
                print(f"    {row}")
    else:
        print(f"  FAIL: {r['error']}")
    results["index_daily"] = r

    print("\n" + "=" * 70)
    print("  3. index_dailybasic — 指数每日 PE/PB/换手率 (最新日)")
    print("=" * 70)
    r = call_tool("index_dailybasic", {"ts_code": index_code, "trade_date": "20260508"})
    if r["success"]:
        print(f"  OK! 记录数: {r['count']}")
        if isinstance(r["data"], list):
            for row in r["data"][:3]:
                print(f"    {row}")
    else:
        print(f"  FAIL: {r['error']}")
    results["index_dailybasic"] = r

    print("\n" + "=" * 70)
    print("  4. index_dailybasic — 指数每日 PE/PB/换手率 (近5日)")
    print("=" * 70)
    r = call_tool("index_dailybasic", {"ts_code": index_code, "start_date": "20260502", "end_date": "20260508"})
    if r["success"]:
        print(f"  OK! 记录数: {r['count']}")
        if isinstance(r["data"], list):
            for row in r["data"][:5]:
                print(f"    {row}")
    else:
        print(f"  FAIL: {r['error']}")
    results["index_dailybasic_range"] = r

    print("\n" + "=" * 70)
    print("  5. daily_basic — 股票每日指标 (上证指数代码)")
    print("=" * 70)
    r = call_tool("daily_basic", {"ts_code": index_code, "trade_date": "20260508"})
    if r["success"]:
        print(f"  OK! 记录数: {r['count']}")
        if isinstance(r["data"], list):
            for row in r["data"][:3]:
                print(f"    {row}")
    else:
        print(f"  FAIL: {r['error']}")
    results["daily_basic"] = r

    print("\n" + "=" * 70)
    print("  6. daily — 股票日线行情 (上证指数代码)")
    print("=" * 70)
    r = call_tool("daily", {"ts_code": index_code, "trade_date": "20260508"})
    if r["success"]:
        print(f"  OK! 记录数: {r['count']}")
        if isinstance(r["data"], list):
            for row in r["data"][:3]:
                print(f"    {row}")
    else:
        print(f"  FAIL: {r['error']}")
    results["daily"] = r

    print("\n" + "=" * 70)
    print("  7. index_classify — 申万行业分类")
    print("=" * 70)
    r = call_tool("index_classify", {"index_code": index_code})
    if r["success"]:
        print(f"  OK! 记录数: {r['count']}")
        if isinstance(r["data"], list):
            for row in r["data"][:3]:
                print(f"    {row}")
    else:
        print(f"  FAIL: {r['error']}")
    results["index_classify"] = r

    print("\n" + "=" * 70)
    print("  8. fund_nav — 基金净值 (华夏300ETF)")
    print("=" * 70)
    r = call_tool("fund_nav", {"ts_code": "510300.SH", "start_date": "20260502", "end_date": "20260508"})
    if r["success"]:
        print(f"  OK! 记录数: {r['count']}")
        if isinstance(r["data"], list):
            for row in r["data"][:5]:
                print(f"    {row}")
    else:
        print(f"  FAIL: {r['error']}")
    results["fund_nav"] = r

    print("\n" + "=" * 70)
    print("  9. etf_basic — ETF基本信息")
    print("=" * 70)
    r = call_tool("etf_basic", {"ts_code": "510300.SH"})
    if r["success"]:
        print(f"  OK! 记录数: {r['count']}")
        if isinstance(r["data"], list):
            for row in r["data"][:3]:
                print(f"    {row}")
    else:
        print(f"  FAIL: {r['error']}")
    results["etf_basic"] = r

    print("\n" + "=" * 70)
    print("  10. etf_share_size — ETF份额规模")
    print("=" * 70)
    r = call_tool("etf_share_size", {"ts_code": "510300.SH", "trade_date": "20260508"})
    if r["success"]:
        print(f"  OK! 记录数: {r['count']}")
        if isinstance(r["data"], list):
            for row in r["data"][:3]:
                print(f"    {row}")
    else:
        print(f"  FAIL: {r['error']}")
    results["etf_share_size"] = r

    print("\n" + "=" * 70)
    print("  11. ths_index — 同花顺概念指数")
    print("=" * 70)
    r = call_tool("ths_index", {"ts_code": "885947.TI"})
    if r["success"]:
        print(f"  OK! 记录数: {r['count']}")
        if isinstance(r["data"], list):
            for row in r["data"][:3]:
                print(f"    {row}")
    else:
        print(f"  FAIL: {r['error']}")
    results["ths_index"] = r

    print("\n" + "=" * 70)
    print("  12. index_member_all — 指数成分股")
    print("=" * 70)
    r = call_tool("index_member_all", {"index_code": "000300.SH"})
    if r["success"]:
        print(f"  OK! 记录数: {r['count']}")
        if isinstance(r["data"], list):
            for row in r["data"][:5]:
                print(f"    {row}")
    else:
        print(f"  FAIL: {r['error']}")
    results["index_member_all"] = r

    print("\n" + "=" * 70)
    print("  测试结果汇总")
    print("=" * 70)
    for name, r in results.items():
        status = "OK" if r["success"] else "FAIL"
        count = r.get("count", "N/A") if r["success"] else r.get("error", "")[:30]
        print(f"  {name:30s} : {status} ({count})")


if __name__ == "__main__":
    main()
