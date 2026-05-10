# 任务拆解

## 输入

- 需求文档：`../pr.md`
- 架构设计：`../architecture/01-architecture-design.md`
- 数据模型：`../data-model/01-data-model.md`
- 工程基建：`../engineering/01-engineering-setup.md`

## 输出

- 按依赖顺序排列的可执行任务清单

## 验收标准（DoD）

- [ ] 每个任务有明确的输入、输出、验收标准
- [ ] 任务间依赖关系清晰，可按顺序执行
- [ ] 每个任务产出可独立验证的代码/产物

---

## 阶段一：项目初始化

### Task 1：项目脚手架搭建

**目标**：初始化 Python 项目，配置好依赖和开发工具

**前置**：无

**执行内容**：
- 创建 pyproject.toml（参照工程基建文档）
- 创建 src/index_score/ 包结构（参照架构设计目录结构）
- 创建所有 __init__.py
- 创建 config.yaml（参照工程基建文档）
- 创建 tests/ 目录
- 创建 report/ 目录 + .gitkeep
- 创建 logs/ 目录 + .gitkeep
- 配置 .gitignore（Python 标准 + report/*.md）
- `pip install -e ".[dev]"`

**验收**：
- [ ] `python -c "import index_score"` 无报错
- [ ] `ruff check src/` 通过
- [ ] `pytest` 可运行（即使无测试）

---

## 阶段二：配置层

### Task 2：配置加载模块

**目标**：实现 config.yaml 的读取和解析

**前置**：Task 1

**执行内容**：
- src/index_score/config/loader.py — 加载 config.yaml
- 按数据模型定义 AppConfig / ScoringConfig / ScoringTemplate / FactorConfig / LLMConfig / ReportConfig / ScoreRange dataclass
- 解析 scoring_templates 配置，构建模板字典
- config.yaml 不存在或格式错误时抛出友好异常
- 编写 tests/test_config.py：正常加载、模板解析、缺失字段、格式错误

**验收**：
- [ ] 可加载 config.yaml 并返回 AppConfig 实例
- [ ] 缺失字段时抛出 ConfigError
- [ ] 测试通过

---

## 阶段三：数据获取层

### Task 3：AkShare 数据拉取器

**目标**：实现从 AkShare 拉取指数行情 + 估值数据

**前置**：Task 2

**执行内容**：
- src/index_score/data/fetcher.py
  - fetch_quote(index_code: str) → IndexQuote
  - fetch_valuation(index_code: str) → IndexValuation
  - fetch_price_history(index_code: str, years: int) → list[IndexQuote]
- 数据字段映射：AkShare 返回列名 → IndexQuote/IndexValuation 字段
- 网络请求异常处理：超时、返回空数据、字段缺失
- 编写 tests/test_data.py：Mock AkShare 返回，验证字段映射和异常处理

**验收**：
- [ ] 能成功拉取一个 A 股指数的行情和估值数据
- [ ] 能成功拉取一个美股指数的数据
- [ ] 异常情况下返回明确错误信息
- [ ] 测试通过

---

### Task 4：数据清洗 + 兜底策略

**目标**：统一数据格式，估值数据走理杏仁 API，行情数据走 AkShare，带重试兜底

**前置**：Task 3

**执行内容**：
- src/index_score/data/cleaner.py
  - clean_quote(raw_data) → IndexQuote
  - clean_valuation(raw_data) → IndexValuation
  - 缺失值处理逻辑
- src/index_score/data/fallback.py
  - fetch_with_fallback(index_code: str) → tuple[IndexQuote, IndexValuation]
  - 估值失败 → 自动重试 3 次（间隔 3 秒） → 降级（缺失因子权重自动重分配）
  - 行情失败 → 自动重试 3 次 → 抛出 FetchError
- 编写 tests/test_data.py 补充测试

**验收**：
- [ ] 理杏仁 API 和 AkShare 返回格式能统一为相同结构
- [ ] Mock 理杏仁 API 失败时，能正确降级为缺失因子
- [ ] 行情和估值都失败时抛出 FetchError
- [ ] 测试通过

---

## 阶段四：量化打分层

### Task 5：模板化打分模型

**目标**：实现基于指数类型模板的打分模型

**前置**：Task 2（配置）

**执行内容**：
- src/index_score/scoring/templates.py
  - 加载 config.yaml 中的 scoring_templates
  - 根据 IndexInfo.template 获取对应的 ScoringTemplate
- src/index_score/scoring/rules.py
  - 分位→分数映射规则（从 config.score_ranges 读取）
- src/index_score/scoring/factor.py
  - score_factor(percentile: float, score_ranges) → FactorScore
  - 通用打分函数，适用于所有因子类型
  - label 映射：1="极便宜" / 3="便宜" / 5="中性" / 7="偏贵" / 9="极贵"
- src/index_score/scoring/calculator.py
  - calculate_price_position(adj_close, high_3y, low_3y) → PricePosition
  - calculate_index_score(index_info, valuation, price_position, template, config) → IndexScore
  - 根据模板配置的因子列表和权重加权计算总分
- 编写 tests/test_scoring.py：
  - 分位边界测试（20%、40%、60%、80%）
  - 模板加载测试（4 种模板各自的因子和权重）
  - 加权计算精度测试
  - 数据缺失时权重重新分配测试

**验收**：
- [ ] 分位 15% → 1 分，分位 25% → 3 分，分位 50% → 5 分
- [ ] 红利型模板：总分 = 股息率×0.4 + PE×0.35 + 价格位置×0.25
- [ ] 价值型模板：总分 = PE×0.4 + PB×0.3 + 股息率×0.3
- [ ] 成长型模板：总分 = PE×0.5 + 价格位置×0.35 + 股息率×0.15
- [ ] 宽基型模板：总分 = PE×0.35 + 股息率×0.35 + 价格位置×0.30
- [ ] 数据缺失时权重按比例重新分配
- [ ] 测试通过

---

## 阶段五：LLM 解读层

### Task 6：LangChain Agent + 投资解读生成

**目标**：集成 LangChain，根据打分结果生成自然语言解读

**前置**：Task 5

**执行内容**：
- src/index_score/llm/prompts.py
  - 系统提示词：定义 Agent 定位、打分逻辑说明、输出格式要求
  - 解读模板：指数名 + 打分 + 因子明细 → 自然语言解读
- src/index_score/llm/agent.py
  - build_agent(config: LLMConfig) → Agent
  - generate_interpretation(index_score: IndexScore) → str
- src/index_score/llm/tools.py
  - 打分查询工具封装（供 LangChain Agent 调用）
  - get_index_score — 查询单个或全部指数打分结果
  - compare_indexes — 对比多个指数的打分和因子差异（V2 预留）
  - get_allocation — 基于打分结果生成配置建议（V2 预留）
  - generate_report — 生成 Markdown 报告
- 编写 tests/test_llm.py：Mock LLM 返回，验证 prompt 拼接和输出格式

**验收**：
- [ ] 能根据 IndexScore 生成包含"当前打分、因子明细、估值水平、投资建议"的解读
- [ ] 支持 DeepSeek / OpenAI 切换（通过配置）
- [ ] LLM API 调用失败时返回兜底文本
- [ ] 测试通过

---

## 阶段六：报告生成层

### Task 7：Markdown 报告生成

**目标**：生成标准化 Markdown 报告

**前置**：Task 6

**执行内容**：
- src/index_score/report/template.py
  - Jinja2 模板：报告标题 / 摘要 / 指数明细表 / 详细分析 / 数据来源
  - 模板严格参照架构设计文档中 report 模块的"报告格式定义"
- src/index_score/report/generator.py
  - generate_report(report_data: ReportData) → str (Markdown 文本)
- src/index_score/report/exporter.py
  - export_report(content: str, date: str) → str (文件路径)
  - 默认保存到 report/指数打分报告_YYYYMMDD.md
- 编写 tests/test_report.py：验证报告结构完整性、文件写入

**验收**：
- [ ] 生成的报告包含摘要、打分明细表、详细分析、数据来源
- [ ] 打分明细表为 Markdown 表格格式
- [ ] 文件名格式正确：指数打分报告_YYYYMMDD.md
- [ ] 测试通过

---

## 阶段七：终端 UI 层

### Task 8：Textual 终端界面

**目标**：实现交互式终端 UI

**前置**：Task 5 + Task 6

**执行内容**：
- src/index_score/ui/app.py — Textual App 主框架
  - 标题区：Agent 名称 + 数据更新时间 + 数据来源
  - 核心表格区：指数名称 / 当前打分 / 各因子分，按打分从低到高排序
  - 交互操作区：【R】刷新数据 【Enter】查看详情 【G】生成报告 【Q】退出
  - 颜色规则：1-3 绿色 / 5 黄色 / 7-9 红色
- src/index_score/ui/widgets/score_table.py — 打分表格组件
- src/index_score/ui/widgets/factor_detail.py — 因子详情面板
- src/index_score/ui/widgets/action_bar.py — 操作按钮栏
- main.py — CLI 入口，启动 Textual App

**验收**：
- [ ] 运行 `python main.py` 启动终端界面
- [ ] 表格正确显示所有指数打分，颜色区分
- [ ] 按快捷键可执行对应操作
- [ ] 查看详情展示因子分位 + LLM 解读

---

## 阶段八：集成联调

### Task 9：端到端集成测试

**目标**：打通完整数据流

**前置**：Task 7 + Task 8

**执行内容**：
- 完整流程测试：启动 → 拉取数据 → 打分 → LLM 解读 → 展示 → 生成报告
- 异常场景测试：API 失败、数据缺失、LLM 超时
- 编写集成测试脚本
- 修复集成过程中发现的问题

**验收**：
- [ ] 完整流程无报错
- [ ] 报告内容正确
- [ ] 异常情况有友好提示

---

## 依赖关系总览

```
Task 1 (脚手架)
  ↓
Task 2 (配置层 + 模板加载)
  ↓
Task 3 (数据拉取) → Task 4 (数据清洗+兜底)
                        ↓
Task 5 (模板化打分) ←───┘
  ↓
Task 6 (LLM 解读)
  ↓
Task 7 (报告生成) ← Task 5
Task 8 (终端 UI)  ← Task 5 + Task 6
  ↓
Task 9 (集成联调) ← Task 7 + Task 8
```
