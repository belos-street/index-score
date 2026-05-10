"""LangChain Agent 工具：指数打分查询。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from index_score.config.models import IndexScore


def create_tools(
    scores: list[IndexScore],
) -> list:
    """根据当前打分结果创建 Agent 可用的工具列表。

    Args:
        scores: 所有指数的打分结果，工具通过闭包访问此数据。

    Returns:
        LangChain tool 列表。
    """
    score_map = {s.code: s for s in scores}

    @tool
    def get_index_score(code: str) -> str:
        """查询单个指数的打分详情。输入指数代码，如 000922、IXIC。"""
        from index_score.llm.prompts import format_index_score

        score = score_map.get(code)
        if score is None:
            available = ", ".join(score_map.keys()) if score_map else "无"
            return f"未找到指数 {code}，可用代码：{available}"
        return format_index_score(score)

    @tool
    def list_all_scores() -> str:
        """列出所有指数的打分摘要。"""
        if not scores:
            return "当前没有可用的打分数据。"

        lines = ["当前所有指数打分：\n"]
        for s in sorted(scores, key=lambda x: x.total_score):
            lines.append(f"- {s.name}({s.code})：{s.total_score}/9（{s.label}）")
        return "\n".join(lines)

    @tool
    def compare_indexes(codes: str) -> str:
        """对比多个指数的打分。输入逗号分隔的指数代码，如 000922,IXIC。"""
        return "对比功能将在 V2 版本中支持，请直接查询各指数详情。"

    @tool
    def generate_report(code: str) -> str:
        """生成指数报告。输入指数代码。"""
        return "报告生成功能将在 V2 版本中支持。"

    return [get_index_score, list_all_scores, compare_indexes, generate_report]
