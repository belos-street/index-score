"""LLM 提示词与格式化工具。"""

from __future__ import annotations

from index_score.config.models import IndexScore

FIELD_LABELS: dict[str, str] = {
    "pe_percentile_5y": "PE_TTM 5年分位",
    "pb_percentile_5y": "PB 5年分位",
    "dividend_yield_percentile_5y": "股息率 5年分位",
    "price_position_percentile_3y": "价格位置 3年分位",
}

SYSTEM_PROMPT = """\
你是一位专业的量化投资分析师，擅长解读指数估值数据。
你的任务是根据指数的量化打分结果，给出专业、客观、易懂的投资解读。

## 打分模型说明

- 评分范围：1.0~9.0（1位小数），分数越低代表越便宜，长期投资价值越高
- 评分基于多因子分位数模型，使用5年滚动窗口百分位作为基准
- 不同类型指数使用不同模板（红利型、价值型、成长型、宽基型），因子权重不同
- 单因子分位越低 = 该指标越便宜

## 估值标签

- 1.0~2.0：极便宜 — 买入信号强烈
- 2.1~4.0：便宜 — 具备安全边际
- 4.1~6.0：中性 — 估值合理区间
- 6.1~8.0：偏贵 — 需谨慎观望
- 8.1~9.0：极贵 — 估值泡沫风险

## 你可用的工具

- get_index_score：查询单个指数的打分详情
- list_all_scores：列出所有指数的打分摘要
- compare_indexes：对比多个指数（V2 预留）
- generate_report：生成报告（V2 预留）

## 输出要求

请用中文回答，包含以下内容：
1. **估值水平判断**：当前处于什么估值水平（便宜/中性/偏贵等）
2. **各因子解读**：逐个分析每个因子的分位和含义
3. **投资建议**：基于量化结果给出简短建议（注意声明仅供参考，不构成投资建议）

语言风格：专业但通俗易懂，避免过度乐观或悲观。篇幅控制在 200 字以内。
"""


def format_index_score(score: IndexScore) -> str:
    """将 IndexScore 格式化为可读文本，包含原始估值绝对值。"""
    lines = [
        f"指数名称：{score.name}（{score.code}）",
        f"打分模板：{score.template}",
        f"数据日期：{score.date}",
        f"综合打分：{score.total_score}/9（{score.label}）",
    ]

    if score.valuation:
        v = score.valuation
        raw_parts: list[str] = []
        if v.pe_ttm is not None:
            raw_parts.append(f"PE(TTM)={v.pe_ttm:.2f}")
        if v.pb_lf is not None:
            raw_parts.append(f"PB={v.pb_lf:.2f}")
        if v.dividend_yield is not None:
            raw_parts.append(f"股息率={v.dividend_yield:.2%}")
        if raw_parts:
            lines.append("原始估值：")
            for p in raw_parts:
                lines.append(f"  - {p}")

    if score.factors:
        lines.append("因子明细：")
        for f in score.factors:
            label = FIELD_LABELS.get(f.field, f.field)
            lines.append(
                f"  - {label}：分位 {f.percentile:.1f}%，"
                f"分数 {f.score:.1f}，权重 {f.weight:.0%}"
            )
    else:
        lines.append("因子明细：数据不足，无法计算")

    if score.price_position_percentile is not None:
        lines.append(
            f"价格位置：{score.price_position_percentile:.1f}%（3年窗口）"
        )

    return "\n".join(lines)


def build_interpretation_query(score: IndexScore) -> str:
    """构建发送给 Agent 的用户查询消息。"""
    detail = format_index_score(score)
    return f"请分析以下指数的估值情况并给出投资建议：\n\n{detail}"
