# index-score 开发 TODO

基于 [task-breakdown](.agents/doc/task-breakdown/01-task-breakdown.md)，按依赖顺序逐项打勾。

---

## 数据源方案：理杏仁 Open API（2026-05-10 确定）

> 详细方案见：[data-model/02-lixinger-api-integration.md](.agents/doc/data-model/02-lixinger-api-integration.md)

**结论**：经过 AkShare / Tushare / 理杏仁三个数据源的全面测试，**理杏仁 Open API 是唯一能完美支持本项目的数据源**。

**理杏仁优势**：
- 一个 API 调用同时返回 PE/PB/股息率 + 5 年分位点 + 最大/最小/20%/50%/80% 分位值
- 覆盖所有 A 股指数（中证、国证、策略指数等），不像 Tushare `index_dailybasic` 只覆盖 5 个大指数
- 支持时间范围查询（日频数据）、批量查询（最多 100 个指数/次）
- 分位点直接返回，无需自己从历史数据计算

**其他数据源的问题**：
- AkShare：无估值历史接口（`index_value_hist_funddb` 已被移除），仅 csindex 可拿 2 个指数的 PE
- Tushare Pro `index_dailybasic`：仅覆盖 5 个宽基指数（上证/深证/沪深300/中证500/创业板），策略指数和 ETF 全部返回空

**数据层架构**：行情数据（AkShare）+ 估值数据（理杏仁 API）双源并行

**Task 3/4 需要重构**：估值拉取逻辑需从 AkShare csindex 重写为理杏仁 API 调用，fallback 策略相应简化。

---

## Task 1：项目脚手架搭建

- [x] 创建 `pyproject.toml`（参照 [engineering](.agents/doc/engineering/01-engineering-setup.md)）
- [x] 创建 `src/index_score/` 包结构（参照 [architecture](.agents/doc/architecture/01-architecture-design.md) 目录结构）
- [x] 创建所有 `__init__.py`
- [x] 创建 `config.yaml`（参照 engineering）
- [x] 创建 `tests/` 目录
- [x] 创建 `report/` 目录 + `.gitkeep`
- [x] 创建 `logs/` 目录 + `.gitkeep`
- [x] 配置 `.gitignore`（Python 标准 + `report/*.md`）
- [x] `pip install -e ".[dev]"`
- [x] 验收：`python -c "import index_score"` 无报错
- [x] 验收：`ruff check src/` 通过
- [x] 验收：`pytest` 可运行

---

## Task 2：配置加载模块

- [x] 定义 dataclass：`IndexInfo` / `FactorConfig` / `ScoringTemplate` / `ScoringConfig` / `ScoreRange` / `LLMConfig` / `ReportConfig` / `AppConfig`（参照 [data-model](.agents/doc/data-model/01-data-model.md)）
- [x] 实现 `src/index_score/config/loader.py`：加载 config.yaml → `AppConfig` 实例
- [x] 实现 `scoring_templates` 解析，构建 `dict[str, ScoringTemplate]`
- [x] config.yaml 不存在或格式错误时抛出 `ConfigError`
- [x] 编写 `tests/test_config.py`：正常加载、模板解析、缺失字段、格式错误
- [x] 验收：`pytest tests/test_config.py` 通过

---

## Task 3：数据拉取器（需重构）

> 原方案基于 AkShare，估值数据严重残缺。现确定使用理杏仁 Open API 作为估值数据源。

- [x] 行情拉取（保留 AkShare）
  - [x] `fetch_quote(index_info) → IndexQuote`（最新行情）
  - [x] `fetch_price_history(index_info, years) → list[IndexQuote]`（历史行情）
- [x] 估值拉取（重写为理杏仁 API）
  - [x] 实现 `src/index_score/data/lixinger.py`：理杏仁 API 客户端
    - [x] `LixingerClient.__init__(token)` 初始化
    - [x] `fetch_fundamental(stock_codes, date, metrics_list) → list[dict]` 指数基本面
  - [x] 重写 `fetch_valuation()` 调用理杏仁 API
    - [x] 请求 `pe_ttm.mcw`, `pb.mcw`, `dyr.mcw`（当前值）
    - [x] 请求 `pe_ttm.y5.mcw.cvpos`, `pb.y5.mcw.cvpos`, `dyr.y5.mcw.cvpos`（5年分位）
  - [x] config.yaml 新增 `lixinger` 配置项 + `lixinger_code` 指数字段
  - [x] `models.py` 新增 `LixingerConfig` + `IndexInfo.lixinger_code`
  - [x] `config/loader.py` 解析 lixinger 配置
  - [x] `data/exceptions.py` 提取共享异常 `FetchError` / `LixingerAPIError`
- [x] 更新 `tests/test_data.py`：Mock 理杏仁 API 返回
- [x] 验收：ruff check + pytest 全部通过（79/79）

---

## Task 4：数据清洗 + 兜底策略（需调整）

> cleaner.py 通用逻辑保留，fallback 策略简化（估值走理杏仁，行情走 AkShare，不再需要 Tushare 切换）。

- [x] `cleaner.py` 保留不变
  - [x] `clean_quote()` OHLC 缺失回退、high/low 互换、NaN volume
  - [x] `clean_valuation()` `0.0` → `None`、负值 PE/PB → `None`
- [x] `fallback.py` 调整
  - [x] `fetch_with_retry()` 通用重试保留
  - [x] `fetch_all()` 整合行情 + 估值拉取 + 清洗，接受 `lixinger_client` 参数
  - [x] 估值失败不再需要 Tushare 切换，直接降级为缺失因子
- [x] 更新 `tests/test_data.py`：适配理杏仁 API mock
- [x] 验收：ruff check + pytest 全部通过（79/79）

---

## Task 5：模板化打分模型

- [x] 实现 `src/index_score/scoring/factor.py`
  - [x] `percentile_to_score(percentile, score_ranges) → float`（分段线性插值，连续 1.0~9.0）
  - [x] `score_to_label(score) → str`（标签映射：极便宜/便宜/中性/偏贵/极贵）
- [x] 实现 `src/index_score/scoring/calculator.py`
  - [x] `calculate_price_position(quotes, years) → float | None`
  - [x] `calculate_index_score(...) → IndexScore`（模板权重加权求和）
  - [x] 数据缺失时权重按比例重新分配
- [x] `models.py` 新增 `FactorScore` / `IndexScore` 数据类
- [x] `ScoreRange.score` 从 `int` 改为 `float`，`loader.py` 解析同步更新
- [x] 编写 `tests/test_scoring.py`（26 个测试用例）
  - [x] 插值边界 / 中点 / 四分位 / 钳位 / 自定义区间 / 精度测试
  - [x] Label 标签映射测试
  - [x] 价格位置：低点 / 高点 / 中点 / 空数据 / 单条 / 平坦测试
  - [x] 4 种模板各自的因子和权重测试
  - [x] 加权计算精度测试
  - [x] 数据缺失权重重分配测试（1个/2个/全部缺失）
  - [x] 分数 1.0~9.0 范围约束测试
- [x] 验收：ruff check + pytest 全部通过（105/105）

---

## Task 6：LangChain Agent + 投资解读生成

- [x] 实现 `src/index_score/llm/prompts.py`
  - [x] 系统提示词：Agent 定位、打分逻辑说明、输出格式要求
  - [x] 解读模板：指数名 + 打分 + 因子明细 → 自然语言解读（`format_index_score` + `build_interpretation_query`）
- [x] 实现 `src/index_score/llm/agent.py`
  - [x] `build_agent(config, scores) → (llm, tools)` — 构建 ChatOpenAI + tools
  - [x] `interpret(llm, tools, score) → str` — Agent 方式调用（create_tool_calling_agent）
  - [x] `interpret_direct(llm, score) → str` — 直接调用（无 tools）
  - [x] `_build_fallback(score) → str` — API 失败/空返回时兜底文本
- [x] 实现 `src/index_score/llm/tools.py`
  - [x] `get_index_score` — 查询单个指数打分详情
  - [x] `list_all_scores` — 列出所有指数打分摘要
  - [x] `compare_indexes` — V2 预留 stub
  - [x] `generate_report` — V2 预留 stub
- [x] 编写 `tests/test_llm.py`：Mock LLM 返回，验证 prompt 拼接、tools、兜底（27 个测试）
- [x] 验收：生成包含"当前打分、因子明细、估值水平、投资建议"的解读
- [x] 验收：支持 DeepSeek / OpenAI 切换（ChatOpenAI 兼容 OpenAI 协议）
- [x] 验收：API 失败时返回兜底文本
- [x] 验收：`pytest tests/test_llm.py` 通过

---

## Task 7：Markdown 报告生成

- [x] 实现 `src/index_score/report/template.py`
  - [x] Jinja2 模板，参照 [architecture](.agents/doc/architecture/01-architecture-design.md) 报告格式定义
  - [x] 4 个章节：摘要 / 打分明细 / 详细分析 / 数据来源与声明
- [x] 实现 `src/index_score/report/generator.py`
  - [x] `generate_report(scores, interpretations, sort_by, generated_at) → str`
  - [x] `ReportSummary` / `AnalysisItem` 数据类，预格式化字段避免模板长行
  - [x] 打分明细表：动态因子列，格式 `分位值(分数)`
- [x] 实现 `src/index_score/report/exporter.py`
  - [x] `export_report(content, date, output_dir) → Path`
  - [x] 保存到 `report/指数打分报告_YYYYMMDD.md`，同日覆盖
- [x] 编写 `tests/test_report.py`：报告结构完整性、文件写入、排序、集成（30 个测试）
- [x] 验收：报告包含摘要、打分明细表、详细分析、数据来源
- [x] 验收：文件名格式正确（`指数打分报告_YYYYMMDD.md`）
- [x] 验收：`pytest tests/test_report.py` 通过

---

## Task 8：Textual 终端界面

- [x] 实现 `src/index_score/ui/app.py` — Textual App 主框架
  - [x] 标题区：Agent 名称 + 数据更新时间 + 数据来源
  - [x] 核心表格区：指数名称 / 当前打分 / 各因子分，按打分从低到高排序
  - [x] 交互操作区：R 刷新 / Enter 详情 / G 报告 / Q 退出
  - [x] 颜色规则：1-3 绿色 / 5 黄色 / 7-9 红色
- [x] 实现 `src/index_score/ui/widgets/score_table.py`
- [x] 实现 `src/index_score/ui/widgets/factor_detail.py`
- [x] 实现 `src/index_score/ui/widgets/action_bar.py`
- [x] 实现 `main.py` — CLI 入口，启动 Textual App
- [x] 验收：`python main.py` 启动终端界面
- [x] 验收：表格正确显示所有指数打分，颜色区分
- [x] 验收：快捷键可执行对应操作
- [x] 验收：详情展示因子分位 + LLM 解读

---

## Task 9：端到端集成测试

- [x] 完整流程测试：启动 → 拉取数据 → 打分 → LLM 解读 → 展示 → 生成报告
- [x] 异常场景测试：API 失败、数据缺失、LLM 超时
- [x] 编写集成测试脚本
- [x] 修复集成过程中发现的问题
- [x] 验收：完整流程无报错
- [x] 验收：报告内容正确
- [x] 验收：异常情况有友好提示

---

## 依赖关系

```
Task 1 (脚手架)
  ↓
Task 2 (配置层)
  ↓
Task 3 (数据拉取: AkShare行情 + 理杏仁估值) → Task 4 (数据清洗+兜底)
                          ↓
Task 5 (模板化打分) ←──────┘
  ↓
Task 6 (LLM 解读)
  ↓
Task 7 (报告生成) ← Task 5
Task 8 (终端 UI)  ← Task 5 + Task 6
  ↓
Task 9 (集成联调) ← Task 7 + Task 8
```
