"""配置数据模型定义。"""

import os
from dataclasses import dataclass


@dataclass
class IndexInfo:
    """指数基础信息。"""

    code: str
    name: str
    market: str
    template: str


@dataclass
class FactorConfig:
    """单因子配置：字段名 + 权重。"""

    field: str
    weight: float


@dataclass
class ScoringTemplate:
    """打分模板：一组因子及权重。"""

    name: str
    factors: list[FactorConfig]


@dataclass
class ScoringConfig:
    """打分配置：所有模板 + 分位年数。"""

    templates: dict[str, ScoringTemplate]
    pe_percentile_years: int
    dividend_yield_percentile_years: int
    price_position_years: int


@dataclass
class ScoreRange:
    """分位→分数映射。"""

    max_percentile: float
    score: int


@dataclass
class LLMConfig:
    """LLM 服务配置。"""

    provider: str
    model: str
    api_key_env: str
    base_url: str
    timeout: int

    @property
    def api_key(self) -> str:
        """从环境变量读取 API Key。"""
        return os.environ.get(self.api_key_env, "")


@dataclass
class ReportConfig:
    """报告输出配置。"""

    show_detail: bool
    sort_by: str


@dataclass
class AppConfig:
    """应用全局配置，聚合所有子配置。"""

    indexes: list[IndexInfo]
    scoring: ScoringConfig
    score_ranges: list[ScoreRange]
    llm: LLMConfig
    report: ReportConfig
