# 架构设计

## 输入

- 需求文档：`../大盘指数量化打分Agent需求文档-初稿.md`

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

**职责**：从 AkShare/Tushare 拉取指数行情和估值数据，清洗为统一格式

**核心组件**：
- `fetcher.py` — 数据拉取器，封装 AkShare API 调用
- `cleaner.py` — 数据清洗，统一字段名、处理缺失值
- `fallback.py` — 兜底策略，AkShare 失败时切换 Tushare

**输入**：指数代码列表
**输出**：标准化的 DataFrame（指数代码、日期、PE/PB/股息率/价格/各分位值）

**依赖**：AkShare、Tushare、Pandas

### 2. scoring — 量化打分层

**职责**：基于 3 因子模型计算每个指数的 0-10 分

**核心组件**：
- `factor.py` — 单因子打分函数（股息率/PE/价格位置 → 1/3/5/7/9 分）
- `calculator.py` — 加权总分计算
- `rules.py` — 打分规则定义（分位区间→分数映射）

**输入**：data 层输出的 DataFrame
**输出**：每个指数的总分 + 各因子分 + 因子分位明细

**依赖**：Pandas、config（权重配置）

### 3. llm — LLM 解读层

**职责**：根据打分结果生成自然语言投资解读

**核心组件**：
- `agent.py` — LangChain Agent 构建
- `prompts.py` — 系统提示词和模板
- `tools.py` — 封装打分查询为 LangChain 工具

**输入**：scoring 层输出的打分结果
**输出**：Markdown 格式的自然语言解读

**依赖**：LangChain、OpenAI/DeepSeek API

### 4. report — 报告生成层

**职责**：将打分结果 + LLM 解读组装为标准化 Markdown 报告

**核心组件**：
- `template.py` — 报告模板（摘要/明细/详细分析/数据来源）
- `generator.py` — 报告生成器，填充模板
- `exporter.py` — 文件导出（保存到 report/ 目录）

**输入**：scoring 结果 + llm 解读
**输出**：`report/指数打分报告_YYYYMMDD.md` 文件

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
data.fetcher 拉取指数数据（AkShare → Tushare 兜底）
    ↓
data.cleaner 清洗为统一 DataFrame
    ↓
scoring.calculator 计算各因子分 + 加权总分
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
│       │   ├── fetcher.py
│       │   ├── cleaner.py
│       │   └── fallback.py
│       ├── scoring/            # 量化打分层
│       │   ├── __init__.py
│       │   ├── factor.py
│       │   ├── calculator.py
│       │   └── rules.py
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
| 缓存策略 | 无持久缓存 | 需求文档明确：关闭 Agent 后数据不保留 |
