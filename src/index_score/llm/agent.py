"""LangChain Agent：构建与调用。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from index_score.llm.prompts import (
    SYSTEM_PROMPT,
    build_interpretation_query,
)
from index_score.llm.tools import create_tools

if TYPE_CHECKING:
    from index_score.config.models import IndexScore, LLMConfig

logger = logging.getLogger(__name__)

_FALLBACK_TEMPLATE = (
    "{name}（{code}）当前综合打分 {score}/9（{label}），"
    "估值水平为{label}。"
    "各因子得分：{factors}。"
    "以上为量化模型自动计算结果，仅供参考，不构成投资建议。"
)

_V2_STUB_MSG = "该功能将在 V2 版本中支持。"


def build_llm(config: LLMConfig) -> ChatOpenAI:
    """根据配置构建 ChatOpenAI 实例（兼容 DeepSeek / OpenAI）。"""
    api_key = config.api_key
    if not api_key:
        raise ValueError(f"LLM API Key 未配置，请在 .env 中设置 {config.api_key_env}")
    return ChatOpenAI(
        model=config.model,
        api_key=api_key,
        base_url=config.base_url if config.base_url else None,
        timeout=config.timeout,
    )


def build_agent(
    config: LLMConfig,
    scores: list[IndexScore],
) -> tuple[ChatOpenAI, list]:
    """构建 LLM 和工具列表。

    Args:
        config: LLM 配置。
        scores: 所有指数打分结果。

    Returns:
        (llm, tools) 元组，供 interpret 使用。
    """
    llm = build_llm(config)
    tools = create_tools(scores)
    return llm, tools


def interpret(
    llm: ChatOpenAI,
    tools: list,
    score: IndexScore,
) -> str:
    """调用 LLM Agent 对单个指数打分结果进行解读。

    Args:
        llm: ChatOpenAI 实例。
        tools: Agent 可用工具列表。
        score: 单个指数的打分结果。

    Returns:
        LLM 生成的解读文本，失败时返回兜底文本。
    """
    query = build_interpretation_query(score)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    try:
        from langchain.agents import AgentExecutor, create_tool_calling_agent

        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            max_iterations=5,
            handle_parsing_errors=True,
        )
        result = executor.invoke({"input": query})
        output = str(result.get("output", "")).strip()
        if output:
            return output
        logger.warning("LLM 返回空内容，使用兜底文本")
        return _build_fallback(score)
    except Exception as exc:
        logger.warning("LLM 调用失败 (%s)，使用兜底文本", exc)
        return _build_fallback(score)


def interpret_direct(
    llm: ChatOpenAI,
    score: IndexScore,
) -> str:
    """直接调用 LLM（不经过 Agent / tools），适用于简单场景。

    Args:
        llm: ChatOpenAI 实例。
        score: 单个指数的打分结果。

    Returns:
        LLM 生成的解读文本，失败时返回兜底文本。
    """
    from langchain_core.messages import HumanMessage

    query = build_interpretation_query(score)

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=query),
        ]
        response = llm.invoke(messages)
        output = str(response.content).strip()
        if output:
            return output
        logger.warning("LLM 返回空内容，使用兜底文本")
        return _build_fallback(score)
    except Exception as exc:
        logger.warning("LLM 调用失败 (%s)，使用兜底文本", exc)
        return _build_fallback(score)


def _build_fallback(score: IndexScore) -> str:
    """构建兜底文本（LLM 不可用时返回）。"""
    factor_parts: list[str] = []
    for f in score.factors:
        factor_parts.append(f"{f.field}={f.score:.1f}({f.label})")
    factors_str = "、".join(factor_parts) if factor_parts else "数据不足"

    return _FALLBACK_TEMPLATE.format(
        name=score.name,
        code=score.code,
        score=score.total_score,
        label=score.label,
        factors=factors_str,
    )
