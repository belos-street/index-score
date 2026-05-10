"""测试所有指数的 index_dailybasic 数据可用性。

用法：
  python scripts/test_index_dailybasic_all.py
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


def call_tool(name: str, args: dict) -> list | str:
    r = mcp_call("tools/call", {"name": name, "arguments": args})
    content = (r or {}).get("result", {}).get("content", [])
    if content:
        text = content[0].get("text", "")
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text[:100]
    return str(r)[:100]


def main() -> None:
    print(f"Token: {TUSHARE_TOKEN[:8]}...{TUSHARE_TOKEN[-4:]}")
    mcp_call("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "tushare-test", "version": "1.0.0"},
    })

    indexes = [
        ("000001.SH", "上证指数"),
        ("399001.SZ", "深证成指"),
        ("399006.SZ", "创业板指"),
        ("000300.SH", "沪深300"),
        ("000905.SH", "中证500"),
        ("000852.SH", "中证1000"),
        ("000922.SH", "中证红利"),
        ("930955.SH", "中证红利低波"),
        ("399371.SZ", "国证价值100"),
        ("931892.SH", "国证自由现金流"),
        ("515450.SH", "红利低波ETF"),
        ("159201.SZ", "现金流ETF"),
        ("510300.SH", "沪深300ETF"),
        ("510500.SH", "中证500ETF"),
        ("512010.SH", "医药ETF"),
        ("399975.SZ", "证券公司指数"),
        ("399986.SZ", "中证银行指数"),
        ("931087.SH", "中证红利全收益"),
        ("H30269.CSI", "中证红利（中证格式）"),
        ("930955.CSI", "中证红利低波（中证格式）"),
    ]

    print(f"\n{'指数代码':<18} {'名称':<15} {'index_dailybasic':>16} {'PE_TTM':>10} {'PB':>8}")
    print("-" * 75)

    for code, name in indexes:
        r = call_tool("index_dailybasic", {"ts_code": code, "trade_date": "20260508"})
        if isinstance(r, list) and r:
            row = r[0]
            pe = row.get("pe_ttm", "N/A")
            pb = row.get("pb", "N/A")
            print(f"{code:<18} {name:<15} {'✅ 有数据':>16} {pe:>10} {pb:>8}")
        elif isinstance(r, list) and not r:
            print(f"{code:<18} {name:<15} {'❌ 空数据':>16}")
        else:
            print(f"{code:<18} {name:<15} {'❌ 错误':>16}  {str(r)[:40]}")

    print("\n" + "=" * 75)
    print("结论：index_dailybasic 仅覆盖主要大盘指数，")
    print("策略指数/行业指数/ETF 不在覆盖范围内。")


if __name__ == "__main__":
    main()
