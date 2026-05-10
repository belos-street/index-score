# 架构设计

## 输入

- 需求文档：`../pr.md`

## 输出

- 项目模块划分、依赖关系、数据流、目录结构

## 验收标准（DoD）

- [ ] 模块边界清晰，每个模块职责单一
- [ ] 数据流从获取→计算→展示→报告的完整链路可追溯
- [ ] 目录结构可直接用于项目初始化

## 整体架构

```
┌─────────────────────────────────────────────────┐
│                   CLI 入口 (main.py)             │
│              Textual App / Click CLI             │
├──────────┬──────────┬───────────┬───────────────┤
│  data    │  scoring │    llm    │    report     │
│  数据层  │  打分层  │  解读层   │    报告层     │
├──────────┴──────────┴───────────┴───────────────┤
│                 config (配置层)                   │
│           index_list / weights / models           │
└─────────────────────────────────────────────────┘
```

## 模块划分

### 1. data — 数据获取层

**职责**：从理杏仁 API 拉取指数估值数据（PE/PB/股息率/分位点），从 AkShare 拉取行情数据，清洗为统一格式

**核心组件**：
- `lixinger.py` — 理杏仁 API 客户端，封装指数基本面数据查询
- `fetcher.py` — 数据拉取器，调用理杏仁 API 获取估值 + AkShare 获取行情
- `cleaner.py` — 数据清洗，统一字段名、处理缺失值
- `fallback.py` — 兜底策略，带重试的数据拉取，估值失败时降级

**输入**：指数代码列表
**输出**：标准化的 DataFrame（指数代码、日期、PE/PB/股息率/价格/各分位值）

**依赖**：理杏仁 Open API、AkShare、requests、Pandas

### 2. scoring — 量化打分层

**职责**：基于指数类型模板计算每个指数的 1-9 分

**核心组件**：
- `factor.py` — 单因子打分函数（分位值 → 1/3/5/7/9 分 + 标签）
- `calculator.py` — 根据模板配置加权计算总分
- `rules.py` — 打分规则定义（分位区间→分数映射）
- `templates.py` — 模板加载与解析（从 config.yaml 读取 scoring_templates）

**输入**：data 层输出的 DataFrame + IndexInfo 中的 template 字段
**输出**：每个指数的总分 + 各因子分 + 因子分位明细

**依赖**：Pandas、config（模板配置）

### 3. llm — LLM 解读层

**职责**：通过 LangChain Agent 根据打分结果生成自然语言投资解读

**核心组件**：
- `agent.py` — LangChain Agent 构建（create_agent + 工具注册）
- `prompts.py` — 系统提示词和解读模板
- `tools.py` — 封装核心业务函数为 LangChain Tool：
  - `get_index_score` — 查询单个或全部指数打分结果
  - `compare_indexes` — 对比多个指数的打分和因子差异（V2）
  - `get_allocation` — 基于打分结果生成仓位配置建议（V2）
  - `generate_report` — 生成 Markdown 报告

**输入**：scoring 层输出的打分结果
**输出**：Markdown 格式的自然语言解读

**依赖**：LangChain、langchain-openai、OpenAI/DeepSeek API

### 4. report — 报告生成层

**职责**：将打分结果 + LLM 解读组装为标准化 Markdown 报告

**核心组件**：
- `template.py` — 报告模板（摘要/明细/详细分析/数据来源）
- `generator.py` — 报告生成器，填充模板
- `exporter.py` — 文件导出（保存到 report/ 目录）

**输入**：scoring 结果 + llm 解读
**输出**：`report/指数打分报告_YYYYMMDD.md` 文件

**报告格式定义**（Jinja2 模板结构）：

```markdown
# 大盘指数量化打分报告

> 生成日期：YYYY-MM-DD HH:MM | 数据来源：理杏仁 API / AkShare

## 摘要

| 指标 | 值 |
|------|---|
| 打分指数数量 | N |
| 平均分 | X.XX |
| 最低分指数 | xxx (X.XX 分) |
| 最高分指数 | xxx (X.XX 分) |
| 整体水平 | 中性偏低/偏高 |

## 打分明细

| 排名 | 指数名称 | 模板 | 股息率分位 | PE分位 | PB分位 | 价格位置 | 总分 | 估值水平 |
|------|---------|------|-----------|-------|-------|---------|------|---------|
| 1 | 中证红利 | dividend | 15.2%(1) | 32.1%(3) | - | 45.3%(5) | 2.60 | 便宜 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

> 因子分位列格式：`分位值(分数)`，不适用的因子标记 `-`

## 指数详细分析

### 1. 中证红利 (000922) — 2.60 分 · 便宜

**估值概况**：PE(TTM) 6.85，近5年分位 32.1%；股息率 5.2%，近5年分位 15.2%

**LLM 解读**：

{llm_interpretation_text}

---

（其余指数同上格式，按总分从低到高排列）

## 数据来源与声明

- 数据更新时间：YYYY-MM-DD HH:MM
- 数据来源：理杏仁 API / AkShare
- 本报告仅供参考，不构成投资建议
```

- 打分明细表的列根据预设指数实际使用的模板动态生成（只显示该模板包含的因子列）
- `sort_by: "score"` 时按总分从低到高排列（便宜的在前）
- 报告中 1-3 分标签"便宜"、5 分"中性"、7-9 分"偏贵"

**依赖**：Markdown、Jinja2（模板）

### 5. config — 配置层

**职责**：管理指数列表、权重、大模型配置等可配置项

**核心文件**：
- `config.yaml` — 主配置文件
- `loader.py` — 配置加载

### 6. ui — 终端 UI 层

**职责**：基于 Textual 的交互式终端界面

**核心组件**：
- `app.py` — Textual App 主入口
- `widgets/` — 自定义组件（打分表格、因子详情面板、操作按钮栏）

**输入**：所有层的输出
**输出**：终端交互界面

**依赖**：Textual、Rich

## 数据流

```
用户启动 App
    ↓
data.fetcher 拉取指数数据
    ├── 理杏仁 API → PE/PB/股息率 + 5年分位点（估值数据）
    └── AkShare → 近3年历史价格（用于计算 price_position）
    ↓
data.cleaner 清洗为统一 DataFrame
    ↓
scoring.calculator 计算各因子分 + 加权总分
    ├── calculate_price_position(adj_close, high_3y, low_3y) → PricePosition
    ├── score_factor(percentile) → FactorScore（按模板配置的因子列表逐个打分）
    └── calculate_index_score(...) → IndexScore（模板权重加权求和）
    ↓
┌───────────────┬──────────────────┐
↓               ↓                  ↓
ui.app 展示     llm.agent 生成     report.generator
打分表格        自然语言解读        生成 Markdown 报告
```

## 项目目录结构

```
index-score/
├── pyproject.toml              # 项目配置 + 依赖声明
├── config.yaml                 # 运行时配置（指数列表/权重/模型）
├── main.py                     # CLI 入口
├── src/
│   └── index_score/
│       ├── __init__.py
│       ├── data/               # 数据获取层
│       │   ├── __init__.py
│       │   ├── lixinger.py     # 理杏仁 API 客户端
│       │   ├── fetcher.py      # 数据拉取（行情 AkShare + 估值理杏仁）
│       │   ├── cleaner.py
│       │   └── fallback.py
│       ├── scoring/            # 量化打分层
│       │   ├── __init__.py
│       │   ├── factor.py
│       │   ├── calculator.py
│       │   ├── rules.py
│       │   └── templates.py
│       ├── llm/                # LLM 解读层
│       │   ├── __init__.py
│       │   ├── agent.py
│       │   ├── prompts.py
│       │   └── tools.py
│       ├── report/             # 报告生成层
│       │   ├── __init__.py
│       │   ├── template.py
│       │   ├── generator.py
│       │   └── exporter.py
│       ├── config/             # 配置层
│       │   ├── __init__.py
│       │   └── loader.py
│       └── ui/                 # 终端 UI 层
│           ├── __init__.py
│           ├── app.py
│           └── widgets/
│               ├── __init__.py
│               ├── score_table.py
│               ├── factor_detail.py
│               └── action_bar.py
├── tests/
│   ├── test_data.py
│   ├── test_scoring.py
│   ├── test_llm.py
│   ├── test_report.py
│   └── test_config.py
├── report/                     # 生成的报告存放目录
├── logs/                       # 日志目录（ERROR 级别写入 logs/app.log）
├── .agents/
└── README.md
```

## 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 包结构 | src layout | 避免 import 歧义，Python 社区推荐 |
| 配置格式 | YAML | 可读性强，支持注释，比 JSON 友好 |
| 模板引擎 | Jinja2 | 报告模板化，与 Python 生态契合 |
| 数据获取 | 手动触发 | 需求文档明确：取消定时任务，仅手动触发 |
| 数据持久化 | 无 | 关闭后数据不保留，每次运行重新拉取 |
| 估值数据源 | 理杏仁 API | 覆盖所有 A 股指数，PE/PB/股息率 + 分位点一次返回 |
| 行情数据源 | AkShare | 历史行情稳定可靠，用于计算价格位置 |
