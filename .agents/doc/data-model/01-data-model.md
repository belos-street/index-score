# 数据模型

## 输入

- 需求文档：`../大盘指数量化打分Agent需求文档-初稿.md`
- 架构设计：`../architecture/01-architecture-design.md`

## 输出

- 所有核心数据结构的 Python 定义
- 数据在各模块间的传递契约

## 验收标准（DoD）

- [ ] 所有数据结构用 Python dataclass/TypedDict 明确定义
- [ ] 字段名、类型、取值范围完整
- [ ] 模块间数据传递格式明确

## 1. 指数基础信息

```python
@dataclass
class IndexInfo:
    code: str              # 指数代码，如 "000922"
    name: str              # 指数名称，如 "中证红利低波"
    market: str            # 市场，"CN" / "US"
```

### 预设指数列表

| code | name | market |
|------|------|--------|
| 000922 | 中证红利 | CN |
| 930955 | 中证红利低波 | CN |
| 930735 | 标普中国红利低波50 | CN |
| 399378 | 国证价值100 | CN |
| 980092 | 国证自由现金流 | CN |
| IXIC | 纳指 | US |
| SPX | 标普500 | US |

## 2. 原始行情数据

从 AkShare/Tushare 拉取后，清洗为统一格式：

```python
@dataclass
class IndexQuote:
    code: str              # 指数代码
    name: str              # 指数名称
    date: str              # 日期，格式 "YYYY-MM-DD"
    open: float            # 开盘价
    close: float           # 收盘价
    high: float            # 最高价
    low: float             # 最低价
    volume: float          # 成交量
    adj_close: float       # 后复权价（用于计算价格位置）
```

## 3. 估值数据

```python
@dataclass
class IndexValuation:
    code: str
    date: str
    pe_ttm: float                  # PE(TTM)
    pe_percentile_3y: float        # PE 近3年分位 (0-100)
    pe_percentile_5y: float        # PE 近5年分位 (0-100)
    pb_lf: float                   # PB(LF)
    pb_percentile_3y: float        # PB 近3年分位 (0-100)
    pb_percentile_5y: float        # PB 近5年分位 (0-100)
    dividend_yield: float          # 股息率 (%)
    dividend_yield_percentile_3y: float   # 股息率近3年分位 (0-100)
    dividend_yield_percentile_5y: float   # 股息率近5年分位 (0-100)
```

## 4. 价格位置（自定义计算）

```python
@dataclass
class PricePosition:
    code: str
    current_price: float           # 当前后复权价
    high_3y: float                 # 近3年最高后复权价
    low_3y: float                  # 近3年最低后复权价
    position: float                # 位置百分比 (0-100)
    # position = (current - low_3y) / (high_3y - low_3y) * 100
```

## 5. 单因子打分结果

```python
@dataclass
class FactorScore:
    name: str                      # 因子名："dividend_yield" / "pe" / "price_position"
    percentile: float              # 分位值 (0-100)
    score: int                     # 打分：1/3/5/7/9
    label: str                     # 标签："极便宜"/"便宜"/"中性"/"偏贵"/"极贵"
```

## 6. 指数打分结果

```python
@dataclass
class IndexScore:
    index_info: IndexInfo
    factor_scores: list[FactorScore]   # 3个因子的打分
    total_score: float                 # 加权总分，保留2位小数
    score_color: str                   # 终端颜色："green"/"yellow"/"red"
    # score_color 规则：
    #   1-3 分 → green
    #   5 分 → yellow
    #   7-9 分 → red
```

## 7. 配置模型

```python
@dataclass
class ScoringConfig:
    dividend_yield_weight: float   # 默认 0.40
    pe_weight: float               # 默认 0.35
    price_position_weight: float   # 默认 0.25
    pe_percentile_years: int       # 默认 5（年）
    dividend_yield_percentile_years: int  # 默认 5
    price_position_years: int      # 默认 3

@dataclass
class ScoreRange:
    min_percentile: float
    max_percentile: float
    score: int

@dataclass
class LLMConfig:
    provider: str                  # "openai" / "deepseek" / "qwen"
    model: str                     # 模型名称
    api_key: str
    base_url: str | None           # 自定义 base_url（国产模型需要）

@dataclass
class AppConfig:
    indexes: list[IndexInfo]
    scoring: ScoringConfig
    score_ranges: list[ScoreRange]
    llm: LLMConfig
```

## 8. 报告数据模型

```python
@dataclass
class ReportData:
    report_date: str                    # "YYYY-MM-DD"
    update_time: str                    # "HH:MM"
    data_source: str                    # "AkShare" / "Tushare"
    index_scores: list[IndexScore]      # 所有指数打分结果
    llm_interpretations: dict[str, str] # 指数代码 → LLM 解读文本
    summary: ReportSummary

@dataclass
class ReportSummary:
    average_score: float
    lowest_index: str
    highest_index: str
    overall_level: str                  # "中性偏低"/"偏高"等
```

## 模块间数据流契约

```
data.fetcher    →  list[IndexQuote] + list[IndexValuation]
                     ↓
scoring.factor  ←  list[IndexValuation] + list[PricePosition]
scoring.calc    →  list[IndexScore]
                     ↓
llm.agent       ←  list[IndexScore]
                  →  dict[str, str]  (code → interpretation)
                     ↓
report.gen      ←  ReportData(IndexScores + interpretations)
                  →  .md 文件
                     ↓
ui.app          ←  list[IndexScore] + dict[str, str]
```
