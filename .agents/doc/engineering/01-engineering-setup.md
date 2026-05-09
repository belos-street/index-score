# 工程基建

## 输入

- 架构设计：`../architecture/01-architecture-design.md`

## 输出

- pyproject.toml 配置
- 依赖清单
- 开发工具配置（lint/format/test）

## 验收标准（DoD）

- [ ] `pip install -e .` 可正常安装
- [ ] `pytest` 可运行测试
- [ ] `ruff check` 和 `ruff format` 可正常工作

## Python 版本

最低要求：Python 3.10+（使用 `X | None` 语法和 `match` 语句）

## 依赖清单

### 核心依赖

| 包 | 用途 | 版本约束 |
|---|------|---------|
| akshare | 财经数据 API（首选） | >=1.14 |
| tushare | 财经数据 API（备选） | >=1.4 |
| pandas | 数据处理 | >=2.0 |
| langchain | LLM Agent 框架 | >=0.3 |
| langchain-openai | OpenAI/兼容 API 集成 | >=0.2 |
| textual | 终端 UI 框架 | >=0.80 |
| rich | 终端美化 | >=13.0 |
| pyyaml | 配置文件解析 | >=6.0 |
| jinja2 | 报告模板引擎 | >=3.1 |

### 开发依赖

| 包 | 用途 |
|---|------|
| pytest | 测试框架 |
| ruff | Lint + Format（替代 flake8 + black） |
| mypy | 类型检查 |

## pyproject.toml 模板

```toml
[project]
name = "index-score"
version = "0.1.0"
description = "大盘指数量化打分 CLI 工具"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
dependencies = [
    "akshare>=1.14",
    "tushare>=1.4",
    "pandas>=2.0",
    "langchain>=0.3",
    "langchain-openai>=0.2",
    "textual>=0.80",
    "rich>=13.0",
    "pyyaml>=6.0",
    "jinja2>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.5",
    "mypy>=1.10",
]

[project.scripts]
index-score = "index_score.main:main"

[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B"]

[tool.mypy]
python_version = "3.10"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
```

## 配置文件 (config.yaml)

```yaml
indexes:
  - code: "000922"
    name: "中证红利"
    market: "CN"
    template: "dividend"
  - code: "930955"
    name: "中证红利低波"
    market: "CN"
    template: "dividend"
  - code: "930735"
    name: "标普中国红利低波50"
    market: "CN"
    template: "dividend"
  - code: "399378"
    name: "国证价值100"
    market: "CN"
    template: "value"
  - code: "980092"
    name: "国证自由现金流"
    market: "CN"
    template: "value"
  - code: "IXIC"
    name: "纳指"
    market: "US"
    template: "growth"
  - code: "SPX"
    name: "标普500"
    market: "US"
    template: "balanced"

scoring:
  templates:
    dividend:
      factors:
        - { field: "dividend_yield_percentile_5y", weight: 0.40 }
        - { field: "pe_percentile_5y", weight: 0.35 }
        - { field: "price_position_percentile_3y", weight: 0.25 }
    value:
      factors:
        - { field: "pe_percentile_5y", weight: 0.40 }
        - { field: "pb_percentile_5y", weight: 0.30 }
        - { field: "dividend_yield_percentile_5y", weight: 0.30 }
    growth:
      factors:
        - { field: "pe_percentile_5y", weight: 0.50 }
        - { field: "price_position_percentile_3y", weight: 0.35 }
        - { field: "dividend_yield_percentile_5y", weight: 0.15 }
    balanced:
      factors:
        - { field: "pe_percentile_5y", weight: 0.35 }
        - { field: "dividend_yield_percentile_5y", weight: 0.35 }
        - { field: "price_position_percentile_3y", weight: 0.30 }
  pe_percentile_years: 5
  dividend_yield_percentile_years: 5
  price_position_years: 3

score_ranges:
  - max_percentile: 20
    score: 1
  - max_percentile: 40
    score: 3
  - max_percentile: 60
    score: 5
  - max_percentile: 80
    score: 7
  - max_percentile: 100
    score: 9

llm:
  provider: "deepseek"
  model: "deepseek-chat"
  api_key: ""
  base_url: "https://api.deepseek.com"
  timeout: 30

report:
  show_detail: true
  sort_by: "score"
```

## 目录初始化脚本

项目创建后需确保以下目录存在：

```bash
mkdir -p report
mkdir -p logs
mkdir -p src/index_score/{data,scoring,llm,report,config,ui/widgets}
mkdir -p tests
```
