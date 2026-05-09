# Python Conventions

本项目 Python 代码规范，与 [engineering 文档](../../../../.agents/doc/engineering/01-engineering-setup.md) 配合使用。

---

## 命名规范

PEP 8 标准，与工程基建文档一致：

| 类型 | 风格 | 示例 |
|------|------|------|
| 文件/目录 | snake_case | `fetcher.py`, `score_table.py` |
| 函数/变量 | snake_case | `fetch_quote`, `score_factor`, `is_valid` |
| 类 | PascalCase | `IndexScore`, `ScoringTemplate` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` |
| 布尔值 | is/has/can 前缀 | `is_valid`, `has_data`, `can_fetch` |
| 私有成员 | _前缀 | `_internal_method` |

## 代码风格

由 ruff 统一管理（lint + format），配置见 `pyproject.toml`：

- 行宽：88 字符
- 缩进：4 空格
- 引号：双引号（ruff 默认）
- 尾随逗号：保留（ruff 默认）
- 导入排序：标准库 → 第三方库 → 本地模块（ruff `I` 规则自动排序）

### 导入风格

```python
# ✅ Good
import logging
from pathlib import Path

import pandas as pd
from pydantic import dataclasses

from index_score.config.loader import AppConfig
from index_score.scoring.factor import score_factor

# ❌ Bad
from index_score.config.loader import *
import pandas, logging
```

## 类型注解

所有公开函数必须有完整的类型注解：

```python
# ✅ Good
def fetch_quote(index_code: str) -> IndexQuote:
    ...

def calculate_index_score(
    index_info: IndexInfo,
    valuation: IndexValuation,
    price_position: PricePosition,
    template: ScoringTemplate,
    config: ScoringConfig,
) -> IndexScore:
    ...

# ❌ Bad
def fetch_quote(index_code):
    ...

def calculate_index_score(index_info, valuation, price_position, template, config):
    ...
```

使用 Python 3.10+ 语法：

```python
# ✅ Good
def get_config() -> AppConfig | None:
    ...

def process(items: list[IndexScore]) -> dict[str, float]:
    ...

# ❌ Bad（旧语法）
from typing import Optional, List, Dict

def get_config() -> Optional[AppConfig]:
    ...

def process(items: List[IndexScore]) -> Dict[str, float]:
    ...
```

## 日志规范

使用 `logging` 模块，禁止 `print` 做正式输出：

```python
logger = logging.getLogger(__name__)

def fetch_quote(index_code: str) -> IndexQuote:
    logger.info("fetching quote for %s", index_code)
    try:
        data = akshare_api(index_code)
    except TimeoutError:
        logger.error("fetch timeout for %s", index_code)
        raise
    return _parse_quote(data)
```

- 每个模块顶部：`logger = logging.getLogger(__name__)`
- 日志级别：`DEBUG`（调试细节）、`INFO`（正常流程）、`WARNING`（降级处理）、`ERROR`（异常但可恢复）、`CRITICAL`（不可恢复）
- 日志格式化用 `%s` 占位符，不要用 f-string（性能）

## 异常处理

规范的 try-except，不裸奔：

```python
# ✅ Good
try:
    quote = fetch_quote(index_code)
except TimeoutError:
    logger.warning("AkShare timeout for %s, trying Tushare", index_code)
    quote = fetch_quote_tushare(index_code)
except Exception:
    logger.exception("unexpected error fetching %s", index_code)
    raise FetchError(f"failed to fetch {index_code}") from None

# ❌ Bad
try:
    quote = fetch_quote(index_code)
except:
    pass
```

- 捕获具体异常类型，不使用裸 `except:`
- 使用 `logger.exception()` 记录完整堆栈
- 自定义异常类继承 `Exception`，不用内置异常名

## Docstring

核心类和公开函数必须有 docstring（Google 风格）：

```python
def score_factor(percentile: float, score_ranges: list[ScoreRange]) -> FactorScore:
    """根据分位值计算单因子打分。

    Args:
        percentile: 分位值 (0-100)。
        score_ranges: 分位→分数映射规则列表。

    Returns:
        包含分数和标签的 FactorScore 实例。

    Raises:
        ValueError: percentile 超出 0-100 范围。
    """
```

## Dataclass 规范

本项目大量使用 dataclass，遵循以下约定：

```python
from dataclasses import dataclass

@dataclass
class IndexScore:
    index_info: IndexInfo
    factor_scores: list[FactorScore]
    total_score: float
    score_color: str
```

- 不用 `@dataclass(frozen=True)` 除非有明确不可变需求
- 字段类型注解必填，默认值放后面
- 配置类用 `@dataclass`，不用 Pydantic BaseModel（简化依赖）

## 测试规范

使用 pytest，AAA 原则（Arrange / Act / Assert）：

```python
def test_score_factor_boundary():
    # Arrange
    score_ranges = [
        ScoreRange(max_percentile=20, score=1),
        ScoreRange(max_percentile=40, score=3),
        ScoreRange(max_percentile=60, score=5),
        ScoreRange(max_percentile=80, score=7),
        ScoreRange(max_percentile=100, score=9),
    ]

    # Act
    result = score_factor(25.0, score_ranges)

    # Assert
    assert result.score == 3
    assert result.label == "便宜"
```

### Mock 策略

- 外部 API（AkShare/Tushare）：使用 `unittest.mock.patch` Mock
- LLM API（DeepSeek/OpenAI）：Mock 返回固定文本
- 文件系统：使用 `tmp_path` fixture

```python
from unittest.mock import patch, MagicMock

@patch("index_score.data.fetcher.akshare")
def test_fetch_quote(mock_akshare):
    mock_akshare.index_zh_a_hist.return_value = pd.DataFrame({...})
    result = fetch_quote("000922")
    assert result.code == "000922"
```

## 项目结构

src layout，参照 [architecture 文档](../../../../.agents/doc/architecture/01-architecture-design.md)：

```
index-score/
├── pyproject.toml
├── config.yaml
├── main.py
├── src/index_score/       # 源码包
├── tests/                 # 测试
├── report/                # 生成的报告
└── logs/                  # 日志
```

- 代码全部在 `src/index_score/` 下，不堆根目录
- 测试文件与源码文件对应：`src/.../fetcher.py` → `tests/test_data.py`
- 配置文件 `config.yaml` 在项目根目录
