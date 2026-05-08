# Agents Guide

本文件为 LLM 提供项目全局认知，包括项目定位、目录结构、文档说明、技能（Skill）清单及调用方式。

***

## 项目概述

**index-score** 是一款大盘指数量化打分工具，基于 Python 技术栈开发，专注于对主流大盘指数进行量化打分（0-10 分，越低越便宜）。面向长期价值投资者和指数基金投资者，通过量化模型替代人工计算，结合 LLM 自然语言解读，降低投资决策门槛。

### 核心功能

- **指数量化打分**：覆盖中证红利、中证红利低波、标普中国红利低波50、国证价值100、国证自由现金流、纳指、标普500等，采用"3因子+加权平均"模型
- **命令行终端展示**：基于 Textual 的组件化终端 UI，彩色表格展示打分结果
- **标准化报告生成**：Markdown 格式投资参考报告，含因子拆解和 LLM 解读

### 技术栈

| 层级    | 技术                                             |
| ----- | ---------------------------------------------- |
| 语言    | Python 3.9+                                    |
| 数据    | AkShare / Tushare + Pandas                     |
| Agent | LangChain + 大模型 API (OpenAI / DeepSeek / 通义千问) |
| 终端 UI | Textual + Rich                                 |
| 报告    | Markdown                                       |
| 缓存    | SQLite                                         |

### 打分模型

- 股息率分位（近5年）权重 40%
- PE 估值分位（近5年）权重 35%
- 价格位置分位（近3年）权重 25%
- 单因子打分：分位 ≤20% → 1分，20-40% → 3分，40-60% → 5分，60-80% → 7分，>80% → 9分
- 总分 = 股息率因子分×40% + PE因子分×35% + 价格位置因子分×25%

***

## 目录结构

```
index-score/
├── agents.md                  # 本文件：LLM 项目导航
├── .agents/
│   ├── doc/                   # 项目文档
│   │   ├── 大盘指数量化打分Agent需求文档-初稿.md
│   │   ├── architecture/
│   │   │   └── 01-architecture-design.md
│   │   ├── data-model/
│   │   │   └── 01-data-model.md
│   │   ├── engineering/
│   │   │   └── 01-engineering-setup.md
│   │   └── task-breakdown/
│   │       └── 01-task-breakdown.md
│   └── skills/                # 可调用技能集合
│       ├── belos-street/      # 编码规范
│       ├── brainstorming/     # 头脑风暴与设计
│       ├── writing-plans/     # 实施计划编写
│       ├── vibe-flow/         # 独立开发者全流程
│       ├── langchain/         # LangChain 框架参考
│       ├── broad-index-etf-analysis/   # 宽基ETF分析
│       ├── buffett-value-investing/    # 巴菲特价值投资
│       ├── cash-flow-etf-analysis/     # 现金流ETF分析
│       ├── dividend-low-vol-etf/       # 红利低波ETF策略
│       ├── fund-comparison/            # 基金对比分析
│       ├── hk-stock-analysis/          # 港股市场分析
│       ├── market-valuation/           # 市场估值判断
│       ├── stock-deep-analysis/        # 个股深度分析
│       └── stock-investment-logic/     # 个股投资逻辑
```

---

## 文档说明 (doc/)

### 需求文档

#### 大盘指数量化打分Agent需求文档-初稿.md

项目的核心需求文档，定义了：

- Agent 的核心定位与目标用户
- 核心功能（量化打分、终端展示、报告生成）与辅助功能（数据获取、LLM解读、异常处理）
- 完整技术栈选型及理由
- 数据获取细节（字段规范、API选择、缓存策略）
- 量化打分逻辑（因子权重、打分规则、总分计算）
- LangChain Agent 实现细节（工具封装、Prompt设计、交互逻辑）
- 终端 UI 布局与视觉规范
- 报告内容结构与导出规范
- 异常处理策略
- 结果展示的详细格式要求

**当需要理解项目需求、实现细节或输出规范时，应参考此文档。**

### 开发文档

#### architecture/01-architecture-design.md — 架构设计

项目模块划分与技术架构，定义了：

- 6 层模块划分：data（数据获取）→ scoring（量化打分）→ llm（LLM解读）→ report（报告生成）→ config（配置）→ ui（终端UI）
- 每层的职责、核心组件、输入输出、依赖关系
- 完整数据流链路：数据拉取 → 清洗 → 打分 → LLM解读 → 展示/报告
- 项目目录结构（src layout）
- 关键设计决策（包结构、配置格式、模板引擎等）

**当需要理解模块间关系、代码组织方式时，应参考此文档。**

#### data-model/01-data-model.md — 数据模型

所有核心数据结构的定义，定义了：

- IndexInfo（指数基础信息）、IndexQuote（行情数据）、IndexValuation（估值数据）
- PricePosition（价格位置）、FactorScore（单因子打分）、IndexScore（指数打分结果）
- AppConfig / ScoringConfig / LLMConfig（配置模型）
- ReportData / ReportSummary（报告数据模型）
- 模块间数据流契约

**当需要编写数据处理代码、理解数据传递格式时，应参考此文档。**

#### engineering/01-engineering-setup.md — 工程基建

项目初始化与开发工具配置，定义了：

- Python 版本要求（3.10+）
- 核心依赖清单（akshare、tushare、pandas、langchain、textual 等）
- pyproject.toml 完整模板
- config.yaml 配置文件模板
- 开发工具配置（ruff lint/format、mypy、pytest）
- 目录初始化脚本

**当需要初始化项目、安装依赖、配置开发工具时，应参考此文档。**

#### task-breakdown/01-task-breakdown.md — 任务拆解

按依赖顺序排列的 9 个可执行任务，覆盖 8 个开发阶段：

- 阶段一：项目脚手架搭建
- 阶段二：配置加载模块
- 阶段三：AkShare 数据拉取器
- 阶段四：数据清洗 + 兜底策略
- 阶段五：单因子打分 + 加权计算
- 阶段六：LangChain Agent + 投资解读生成
- 阶段七：Markdown 报告生成
- 阶段八：Textual 终端界面
- 阶段九：端到端集成测试

每个任务包含：目标、前置依赖、执行内容、验收标准（DoD checklist）

**当需要开始编码实现时，应按此文档的任务顺序依次执行。**

***

## 技能清单 (skills/)

### 开发流程类

#### brainstorming — 头脑风暴与设计

- **用途**：创建功能、构建组件、添加新行为之前，先通过结构化对话探索用户意图、需求和设计
- **核心流程**：探索项目上下文 → 提问澄清 → 提出2-3种方案 → 呈现设计 → 用户确认 → 编写设计文档 → 自审 → 调用 writing-plans
- **硬性约束**：在用户批准设计之前，禁止编写任何代码或执行任何实现操作
- **产出**：设计文档 `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- **触发条件**：任何创造性工作（新功能、新组件、新行为）

#### writing-plans — 实施计划编写

- **用途**：拿到设计规格后，将其拆解为可执行的、逐步骤的实施计划
- **核心原则**：每步 2-5 分钟粒度、完整代码（无占位符）、TDD、精确文件路径、频繁提交
- **产出**：实施计划文档 `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
- **触发条件**：已有设计规格或需求文档，准备开始编码前
- **执行方式**：支持 Subagent-Driven（推荐）和 Inline Execution 两种模式

#### vibe-flow — 独立开发者全流程

- **用途**：独立开发者从项目想法到上线变现的完整 14 阶段流水线
- **14 个阶段**：商业立项 → 需求工程 → 交互原型 → UI设计 → 架构设计 → 数据建模 → API契约 → 工程基建 → 任务拆解 → 编码 → 测试 → 部署 → 文档 → 迭代
- **核心机制**：主线顺序推进 + 可控回流（范围/交互/数据/架构变化时强制回到对应阶段修正）
- **触发条件**：启动新的 Web/SaaS 项目
- **适用范围**：独立开发者主导的 Web/SaaS、管理后台、工具类产品

#### belos-street — 编码规范

- **用途**：个人编码习惯与最佳实践，确保项目代码风格一致性
- **覆盖内容**：命名规范（kebab-case 文件名、camelCase 变量、PascalCase 类型）、代码组织、代码风格、测试理念、LLM 编码指南
- **触发条件**：编写任何代码时自动遵循
- **速查**：文件 kebab-case，组件 kebab-case，函数/变量 camelCase，接口/类型 PascalCase，常量 UPPER\_SNAKE\_CASE，布尔 is/has/can 前缀

#### langchain — LangChain 框架参考

- **用途**：构建 AI Agent 和 LLM 应用的框架参考文档
- **覆盖内容**：Agent 架构、模型集成、工具定义、消息格式、内存管理、流式输出、结构化输出、中间件、Prompt 模板、RAG、错误处理
- **触发条件**：开发 LangChain 相关功能时参考
- **关键导入**：`from langchain.agents import create_agent`、`from langchain.tools import tool`

***

### 投资分析类

#### broad-index-etf-analysis — 宽基指数ETF分析

- **用途**：分析宽基指数ETF投资策略，提供对比分析、估值分析、投资时机判断
- **覆盖范围**：沪深300、中证500、中证1000、中证A500、创业板指、科创50、恒生指数等
- **分析维度**：市值覆盖、行业分布、估值水平（PE/PB/股息率）、波动性、收益对比
- **触发关键词**：宽基ETF、A500、沪深300、中证500、宽基投资

#### buffett-value-investing — 巴菲特价值投资分析

- **用途**：基于巴菲特价值投资四大原则（能力圈、护城河、安全边际、长期持有）进行个股分析
- **分析流程**：能力圈验证 → 护城河评估（成本/品牌/技术/客户转换成本/渠道）→ 安全边际测算（DCF/PEG）→ 长期持有可行性 → 投资决策 → 风险提示
- **输出**：标准化的巴菲特理念分析报告，含建仓策略、持有纪律、风险对冲
- **触发关键词**：价值投资、巴菲特理念、个股价值分析

#### cash-flow-etf-analysis — 现金流ETF分析

- **用途**：分析现金流ETF投资策略，识别现金流标的，评估现金流稳定性
- **覆盖资产**：高股息股票、REITs、公用事业、基础设施
- **分析维度**：收现比、净现比、自由现金流、分红稳定性、分红增长性
- **触发关键词**：现金流ETF、现金流投资、分红收益

#### dividend-low-vol-etf — 红利低波ETF策略

- **用途**：分析红利低波ETF的加仓减仓时机、风险评估、持仓管理
- **加仓信号**：估值低位（PE/PB历史分位低、股息率高位）、技术面支撑、利率下行、资金流入
- **减仓信号**：估值高位、技术面超买、市场过热
- **策略工具**：分批加仓法（金字塔/定投）、事件驱动加仓
- **触发关键词**：红利低波ETF、加仓减仓、仓位管理

#### fund-comparison — 基金对比分析

- **用途**：对多只基金进行全方位、多维度深度对比，生成专业投资分析报告
- **对比维度**：业绩（多周期收益率）、风险（最大回撤/夏普/卡玛比率）、持仓（资产配置/行业/重仓股）、基金经理、费用
- **两种模式**：客观分析模式（中立对比）vs 主观分析模式（倾向性分析）
- **触发关键词**：基金对比、基金替换、基金组合优化

#### hk-stock-analysis — 港股市场分析

- **用途**：分析港股市场行情、交易规则、南北资金流向、港股与A股联动性
- **覆盖内容**：恒生指数/恒生科技/恒生医疗、交易规则（T+2/无涨跌幅限制/市调机制）、费用结构、南向资金流向
- **触发关键词**：港股投资、港股ETF、港股与A股对比

#### market-valuation — 市场估值判断

- **用途**：通过万得全A、沪深300、上证指数的历史分位数判断A股市场整体估值高低
- **判断标准**：极度低估（PE分位<15%）→ 低估（<30%）→ 合理偏低（30-50%）→ 合理偏高（50-70%）→ 高估（>70%）→ 极度高估（>85%）
- **风格判断**：万得全A vs 沪深300 估值差异 → 成长/价值/均衡风格
- **触发关键词**：市场估值、A股高低判断、市场位置

#### stock-deep-analysis — 个股深度分析

- **用途**：提供个股基本面分析、估值分析、技术面辅助、风险评估
- **分析维度**：公司概况、财务指标（盈利/成长/健康/现金流）、业务模式、产业链位置、竞争优势、估值方法（PE/PB/PEG/DCF）、技术面趋势
- **触发关键词**：个股分析、股票投资建议、财务数据

#### stock-investment-logic — 个股投资逻辑研究

- **用途**：生成接近券商研究员风格的高质量个股分析报告
- **报告结构**：公司概况 → 投资逻辑（核心逻辑+成长驱动+护城河）→ 财务分析 → 估值分析 → 风险分析 → 竞争格局（波特五力）→ 投资建议
- **定位**：比 stock-deep-analysis 更侧重投资逻辑梳理和机构研究视角
- **触发关键词**：个股分析、投资逻辑、深度研究

***

## 技能调用方式

在 IDE 中，技能通过 `Skill` 工具调用，只需传入技能名称：

| 场景             | 推荐技能                     | 调用名                        |
| -------------- | ------------------------ | -------------------------- |
| 开始新功能设计        | brainstorming            | `brainstorming`            |
| 编写实施计划         | writing-plans            | `writing-plans`            |
| 启动新项目全流程       | vibe-flow                | `vibe-flow`                |
| 编码时遵循规范        | belos-street             | `belos-street`             |
| 查 LangChain 用法 | langchain                | `langchain`                |
| 分析宽基ETF        | broad-index-etf-analysis | `broad-index-etf-analysis` |
| 个股价值投资分析       | buffett-value-investing  | `buffett-value-investing`  |
| 现金流ETF分析       | cash-flow-etf-analysis   | `cash-flow-etf-analysis`   |
| 红利低波ETF操作      | dividend-low-vol-etf     | `dividend-low-vol-etf`     |
| 多基金对比          | fund-comparison          | `fund-comparison`          |
| 港股市场分析         | hk-stock-analysis        | `hk-stock-analysis`        |
| 判断市场估值         | market-valuation         | `market-valuation`         |
| 个股深度分析         | stock-deep-analysis      | `stock-deep-analysis`      |
| 个股投资逻辑研究       | stock-investment-logic   | `stock-investment-logic`   |

### 技能调用时机判断

**当用户请求涉及以下意图时，应立即调用对应技能：**

1. **设计/规划阶段**：任何新功能、新组件、新行为的创建 → `brainstorming`
2. **实施阶段**：已有设计规格，需要编写代码 → `writing-plans`
3. **编码阶段**：编写代码时 → 遵循 `belos-street` 规范
4. **投资分析阶段**：用户询问投资相关问题 → 调用对应投资分析技能

**投资分析技能的选择逻辑：**

- 用户问的是"大盘/市场整体估值" → `market-valuation`
- 用户问的是"宽基指数ETF"（沪深300/中证500等） → `broad-index-etf-analysis`
- 用户问的是"红利低波ETF的操作策略" → `dividend-low-vol-etf`
- 用户问的是"现金流/分红收益" → `cash-flow-etf-analysis`
- 用户问的是"港股" → `hk-stock-analysis`
- 用户问的是"某只基金好不好"或"多只基金对比" → `fund-comparison`
- 用户问的是"某只股票的价值投资分析"（巴菲特视角） → `buffett-value-investing`
- 用户问的是"某只股票的深度分析"（综合视角） → `stock-deep-analysis`
- 用户问的是"某只股票的投资逻辑"（券商研报风格） → `stock-investment-logic`

***

## 开发指南

### 项目上下文

- 当前项目处于初始阶段，主要代码结构待搭建
- 核心需求文档位于 `.agents/doc/大盘指数量化打分Agent需求文档-初稿.md`
- 所有开发应严格遵循需求文档中定义的功能边界和技术规范

### 编码规范

遵循 `belos-street` 技能定义的编码规范：

- 文件/目录命名：kebab-case
- 函数/变量：camelCase
- 接口/类型：PascalCase
- 常量：UPPER\_SNAKE\_CASE
- 布尔值：is/has/can 前缀
- 核心原则：一致性优先 > 描述性 > 简洁 > 避免缩写

### Agent 开发要点

- 使用 LangChain 的 `create_agent` 创建 Agent
- 将数据拉取、打分计算、报告生成封装为 LangChain 工具
- 支持多模型切换（OpenAI / DeepSeek / 通义千问）
- 系统提示词需明确 Agent 定位、打分逻辑、输出格式

