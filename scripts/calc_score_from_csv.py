"""用理杏仁 CSV 数据计算红利低波指数打分。

三个 CSV 文件：
  1. 红利低波100_股息率_市值加权_上市以来_20260510_134119.csv
  2. 红利低波100_PE-TTM_市值加权_上市以来_20260510_135001.csv
  3. 红利低波100_PB_市值加权_上市以来_20260510_135046.csv

打分模板（红利型 dividend）：
  - 股息率分位 × 0.40
  - PE 分位 × 0.35
  - 价格位置 × 0.25

用法：
  python scripts/calc_score_from_csv.py
"""

from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_DIVIDEND = DATA_DIR / "红利低波100_股息率_市值加权_上市以来_20260510_134119.csv"
CSV_PE = DATA_DIR / "红利低波100_PE-TTM_市值加权_上市以来_20260510_135001.csv"
CSV_PB = DATA_DIR / "红利低波100_PB_市值加权_上市以来_20260510_135046.csv"

SCORE_RANGES = [
    (0.20, 1),
    (0.40, 3),
    (0.60, 5),
    (0.80, 7),
    (1.00, 9),
]

LABELS = {1: "极便宜", 3: "便宜", 5: "中性", 7: "偏贵", 9: "极贵"}

DIVIDEND_TEMPLATE = {
    "dividend_yield_percentile_5y": 0.40,
    "pe_percentile_5y": 0.35,
    "price_position_percentile_3y": 0.25,
}


def percentile_to_score(p: float) -> int:
    if p is None:
        return 5
    for max_p, score in SCORE_RANGES:
        if p <= max_p:
            return score
    return 9


def parse_csv(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        raw = f.read()
    lines = raw.strip().split("\n")
    header = lines[0].split(",")
    for line in lines[1:]:
        if line.startswith("数据来源"):
            continue
        vals = line.split(",")
        row = {}
        for i, h in enumerate(header):
            v = vals[i].strip() if i < len(vals) else ""
            if v.startswith("="):
                v = v[1:]
            row[h.strip()] = v
        rows.append(row)
    return rows


def merge_data(div_rows, pe_rows, pb_rows):
    by_date: dict[str, dict] = {}
    for row in div_rows:
        d = row["日期"]
        by_date[d] = {
            "日期": d,
            "收盘点位": row.get("收盘点位", ""),
            "股息率": _safe_float(row.get("股息率市值加权", "")),
            "股息率分位": _safe_float(row.get("股息率 分位点", "")),
            "PE_TTM": None,
            "PE分位": None,
            "PB": None,
            "PB分位": None,
        }
    for row in pe_rows:
        d = row["日期"]
        if d not in by_date:
            by_date[d] = {
                "日期": d,
                "收盘点位": row.get("收盘点位", ""),
                "股息率": None,
                "股息率分位": None,
                "PE_TTM": None,
                "PE分位": None,
                "PB": None,
                "PB分位": None,
            }
        by_date[d]["PE_TTM"] = _safe_float(row.get("PE-TTM市值加权", ""))
        by_date[d]["PE分位"] = _safe_float(row.get("PE-TTM 分位点", ""))
    for row in pb_rows:
        d = row["日期"]
        if d not in by_date:
            by_date[d] = {
                "日期": d,
                "收盘点位": row.get("收盘点位", ""),
                "股息率": None,
                "股息率分位": None,
                "PE_TTM": None,
                "PE分位": None,
                "PB": None,
                "PB分位": None,
            }
        by_date[d]["PB"] = _safe_float(row.get("PB市值加权", ""))
        by_date[d]["PB分位"] = _safe_float(row.get("PB 分位点", ""))
    return sorted(by_date.values(), key=lambda r: r["日期"], reverse=True)


def _safe_float(v: str):
    if not v:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def main() -> None:
    print("=" * 60)
    print("  红利低波指数打分 — 理杏仁 CSV 数据（完整版）")
    print("=" * 60)

    div_rows = parse_csv(CSV_DIVIDEND)
    pe_rows = parse_csv(CSV_PE)
    pb_rows = parse_csv(CSV_PB)
    merged = merge_data(div_rows, pe_rows, pb_rows)

    print(f"\n数据行数: {len(merged)}")
    print(f"时间跨度: {merged[-1]['日期']} ~ {merged[0]['日期']}")

    latest = merged[0]
    print(f"\n{'=' * 60}")
    print(f"  最新数据（{latest['日期']}）")
    print(f"{'=' * 60}")
    print(f"  收盘点位:     {latest['收盘点位']}")
    print(
        f"  股息率:       {latest['股息率'] * 100:.2f}%"
        if latest["股息率"]
        else "  股息率:       N/A"
    )
    print(
        f"  股息率分位:   {latest['股息率分位'] * 100:.1f}%"
        if latest["股息率分位"]
        else "  股息率分位:   N/A"
    )
    print(
        f"  PE_TTM:       {latest['PE_TTM']:.4f}"
        if latest["PE_TTM"]
        else "  PE_TTM:       N/A"
    )
    print(
        f"  PE分位:       {latest['PE分位'] * 100:.1f}%"
        if latest["PE分位"]
        else "  PE分位:       N/A"
    )
    print(
        f"  PB:           {latest['PB']:.4f}" if latest["PB"] else "  PB:           N/A"
    )
    print(
        f"  PB分位:       {latest['PB分位'] * 100:.1f}%"
        if latest["PB分位"]
        else "  PB分位:       N/A"
    )

    div_pct = latest["股息率分位"]
    pe_pct = latest["PE分位"]

    print(f"\n{'=' * 60}")
    print("  因子1: 股息率分位 (权重 40%)")
    print(f"{'=' * 60}")
    if div_pct is not None:
        div_score = percentile_to_score(div_pct)
        print(f"  分位点: {div_pct:.4f} ({div_pct * 100:.1f}%)")
        print(f"  打分: {div_score} ({LABELS[div_score]})")
    else:
        div_score = None
        print("  ❌ 无数据")

    print(f"\n{'=' * 60}")
    print("  因子2: PE_TTM 分位 (权重 35%)")
    print(f"{'=' * 60}")
    if pe_pct is not None:
        pe_score = percentile_to_score(pe_pct)
        print(f"  PE_TTM: {latest['PE_TTM']:.4f}")
        print(f"  分位点: {pe_pct:.4f} ({pe_pct * 100:.1f}%)")
        print(f"  打分: {pe_score} ({LABELS[pe_score]})")
    else:
        pe_score = None
        print("  ❌ 无数据")

    print(f"\n{'=' * 60}")
    print("  因子3: 价格位置分位 (权重 25%)")
    print(f"{'=' * 60}")
    closes = [(r["日期"], _safe_float(r["收盘点位"])) for r in merged]
    closes = [(d, c) for d, c in closes if c is not None]

    if len(closes) >= 4:
        current = closes[0][1]
        recent_3y = [c for _, c in closes[:4]]
        high_3y = max(recent_3y)
        low_3y = min(recent_3y)
        if high_3y != low_3y:
            price_pct = max(0.0, min(1.0, (current - low_3y) / (high_3y - low_3y)))
        else:
            price_pct = 0.5
        price_score = percentile_to_score(price_pct)
        print(f"  近3年数据点: {', '.join(f'{d}={c:.2f}' for d, c in closes[:4])}")
        print(f"  3年最高: {high_3y:.2f}")
        print(f"  3年最低: {low_3y:.2f}")
        print(f"  当前:    {current:.2f}")
        print(f"  价格位置分位: {price_pct:.4f} ({price_pct * 100:.1f}%)")
        print(f"  打分: {price_score} ({LABELS[price_score]})")
    else:
        price_pct = None
        price_score = None
        print("  ❌ 数据不足")

    print(f"\n{'=' * 60}")
    print("  综合打分（红利型模板）")
    print(f"{'=' * 60}")

    factors = {}
    if div_pct is not None and div_score is not None:
        factors["股息率分位"] = (
            "dividend_yield_percentile_5y",
            div_pct,
            0.40,
            div_score,
        )
    if pe_pct is not None and pe_score is not None:
        factors["PE_TTM分位"] = ("pe_percentile_5y", pe_pct, 0.35, pe_score)
    if price_pct is not None and price_score is not None:
        factors["价格位置分位"] = (
            "price_position_percentile_3y",
            price_pct,
            0.25,
            price_score,
        )

    total_weight = sum(w for _, _, w, _ in factors.values())

    print(f"\n  可用因子: {len(factors)}/3，权重合计: {total_weight:.2f}")
    if total_weight < 1.0:
        print("  权重重分配: 按比例放大到 1.0")

    print(f"\n  {'因子':<20} {'原始权重':>8} {'调整权重':>8} {'分位':>8} {'分数':>6}")
    print(f"  {'-' * 55}")

    total_score = 0.0
    for label, (field, pct, orig_w, score) in factors.items():
        adj_w = orig_w / total_weight if total_weight > 0 else 0
        contribution = score * adj_w
        total_score += contribution
        print(
            f"  {label:<20} {orig_w:>7.2f} {adj_w:>7.2f} {pct * 100:>7.1f}% {score:>5}"
        )

    missing_fields = []
    if "股息率分位" not in factors:
        missing_fields.append("股息率分位(0.40)")
    if "PE_TTM分位" not in factors:
        missing_fields.append("PE_TTM分位(0.35)")
    if "价格位置分位" not in factors:
        missing_fields.append("价格位置分位(0.25)")
    for mf in missing_fields:
        print(f"  {mf:<20} {'跳过':>8} {'—':>8} {'N/A':>8} {'—':>5}")

    total_score = round(total_score, 2)
    final_label = LABELS.get(
        min(SCORE_RANGES, key=lambda r: abs(r[1] - total_score))[1], "中性"
    )

    print(f"  {'-' * 55}")
    print(f"  {'加权总分':<20} {'':>8} {'':>8} {'':>8} {total_score:>5.2f}")

    print(f"\n{'=' * 60}")
    print("  结论")
    print(f"{'=' * 60}")
    print(f"  红利低波指数 当前打分: {total_score:.2f} / 9")
    print(f"  估值水平: {final_label}")
    if latest["股息率"] and latest["股息率分位"]:
        print(
            f"  股息率: {latest['股息率'] * 100:.2f}% (分位 {latest['股息率分位'] * 100:.1f}%)"
        )
    if latest["PE_TTM"] and latest["PE分位"]:
        print(f"  PE_TTM: {latest['PE_TTM']:.2f} (分位 {latest['PE分位'] * 100:.1f}%)")
    if latest["PB"] and latest["PB分位"]:
        print(f"  PB:     {latest['PB']:.2f} (分位 {latest['PB分位'] * 100:.1f}%)")
    if len(factors) == 3:
        print("\n  ✅ 三个因子全部可用，打分结果完整")
    else:
        print(f"\n  ⚠️ 仅 {len(factors)}/3 个因子可用")

    print(f"\n{'=' * 60}")
    print("  历史估值变化（理杏仁年度快照）")
    print(f"{'=' * 60}")
    print(
        f"  {'日期':<14} {'收盘':>10} {'股息率':>8} {'股息率分位':>10} {'PE_TTM':>8} {'PE分位':>8} {'PB':>6} {'PB分位':>8}"
    )
    print(f"  {'-' * 80}")
    for r in merged:
        dy = f"{r['股息率'] * 100:.2f}%" if r["股息率"] else "N/A"
        dp = f"{r['股息率分位'] * 100:.1f}%" if r["股息率分位"] else "N/A"
        pe = f"{r['PE_TTM']:.2f}" if r["PE_TTM"] else "N/A"
        pp = f"{r['PE分位'] * 100:.1f}%" if r["PE分位"] else "N/A"
        pb = f"{r['PB']:.2f}" if r["PB"] else "N/A"
        bp = f"{r['PB分位'] * 100:.1f}%" if r["PB分位"] else "N/A"
        close = r["收盘点位"] or "N/A"
        print(
            f"  {r['日期']:<14} {close:>10} {dy:>8} {dp:>10} {pe:>8} {pp:>8} {pb:>6} {bp:>8}"
        )


if __name__ == "__main__":
    main()
