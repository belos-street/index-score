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
    lixinger_code: str | None = None


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
class LixingerConfig:
    """理杏仁 Open API 配置。"""

    token_env: str
    base_url: str
    timeout: int

    @property
    def token(self) -> str:
        """从环境变量读取 Token。"""
        return os.environ.get(self.token_env, "")


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
    lixinger: LixingerConfig | None = None
    report: ReportConfig | None = None


@dataclass
class IndexQuote:
    """指数行情数据。"""

    code: str
    name: str
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float
    adj_close: float


@dataclass
class IndexValuation:
    """指数估值数据。

    估值绝对值和百分位字段使用 float | None：
    - None 表示该指标暂无数据（打分模块会跳过并重新分配权重）
    - 0.0 表示实际计算值为 0（如股息率为 0 意味着无分红）
    """

    code: str
    date: str
    pe_ttm: float | None = None
    pe_percentile_5y: float | None = None
    pb_lf: float | None = None
    pb_percentile_5y: float | None = None
    dividend_yield: float | None = None
    dividend_yield_percentile_5y: float | None = None
