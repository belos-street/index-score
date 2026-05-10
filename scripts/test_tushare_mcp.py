"""通过 Tushare Pro MCP 服务测试指数估值数据。

认证方式: Authorization: Bearer {token}

用法：
  python scripts/test_tushare_mcp.py
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


def call_tool(name: str, args: dict, label: str = "") -> dict | None:
    print(f"\n{'=' * 70}")
    print(f"  {label or name}")
    print(f"  参数: {json.dumps(args, ensure_ascii=False)}")
    print("=" * 70)

    r = mcp_call("tools/call", {"name": name, "arguments": args})
    content = (r or {}).get("result", {}).get("content", [])
    is_error = (r or {}).get("result", {}).get("isError", False)

    if content:
        text = content[0].get("text", "")
        try:
            data = json.loads(text)
            if isinstance(data, list) and data:
                print(f"  记录数: {len(data)}")
                for row in data[:5]:
                    print(f"    {row}")
                if len(data) > 5:
                    print(f"    ... 共 {len(data)} 条")
            elif isinstance(data, list) and not data:
                print("  空数据")
            else:
                s = json.dumps(data, indent=2, ensure_ascii=False)
                print(s[:1500])
        except (json.JSONDecodeError, TypeError):
            print(f"  {text[:1500]}")
    elif is_error:
        print(f"  Error: {json.dumps(r, ensure_ascii=False)[:500]}")
    else:
        print(f"  返回: {json.dumps(r, indent=2, ensure_ascii=False)[:1000]}")

    return r


def main() -> None:
    print(f"Token: {TUSHARE_TOKEN[:8]}...{TUSHARE_TOKEN[-4:]}")

    print("\n" + "=" * 70)
    print("  Step 0: MCP initialize 握手")
    print("=" * 70)
    r = mcp_call(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "tushare-test", "version": "1.0.0"},
        },
    )
    print(f"  Server: {r.get('result', {}).get('serverInfo', {})}")

    print("\n\n" + "#" * 70)
    print("#  1. index_basic — 指数基本信息")
    print("#" * 70)
    for code, name in [
        ("000922.SH", "中证红利"),
        ("930955.SH", "中证红利低波"),
        ("399371.SZ", "国证价值100"),
        ("000300.SH", "沪深300（对照）"),
        ("000905.SH", "中证500（对照）"),
    ]:
        call_tool("index_basic", {"ts_code": code}, f"index_basic - {name}")

    print("\n\n" + "#" * 70)
    print("#  2. index_dailybasic — 指数每日 PE/PB")
    print("#" * 70)
    for code, name in [
        ("000922.SH", "中证红利"),
        ("930955.SH", "中证红利低波"),
        ("399371.SZ", "国证价值100"),
        ("000300.SH", "沪深300"),
        ("000905.SH", "中证500"),
    ]:
        call_tool(
            "index_dailybasic",
            {"ts_code": code, "trade_date": "20260508"},
            f"index_dailybasic - {name}",
        )

    print("\n\n" + "#" * 70)
    print("#  3. fund_daily — ETF 日线行情")
    print("#" * 70)
    for code, name in [
        ("515450.SH", "红利低波ETF"),
        ("159201.SZ", "现金流ETF"),
        ("510300.SH", "沪深300ETF（对照）"),
    ]:
        call_tool(
            "fund_daily",
            {"ts_code": code, "trade_date": "20260508"},
            f"fund_daily - {name}",
        )

    print("\n\n" + "#" * 70)
    print("#  4. daily_basic — 股票每日指标（PE/PB/股息率）")
    print("#" * 70)
    for code, name in [
        ("515450.SH", "红利低波ETF"),
        ("159201.SZ", "现金流ETF"),
        ("000300.SH", "沪深300指数代码"),
    ]:
        call_tool(
            "daily_basic",
            {"ts_code": code, "trade_date": "20260508"},
            f"daily_basic - {name}",
        )

    print("\n\n" + "#" * 70)
    print("#  5. fund_basic — 基金基本信息")
    print("#" * 70)
    for code, name in [
        ("515450.SH", "红利低波ETF"),
        ("159201.SZ", "现金流ETF"),
    ]:
        call_tool("fund_basic", {"ts_code": code}, f"fund_basic - {name}")

    print("\n\n" + "=" * 70)
    print("  测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
