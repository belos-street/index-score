# 大盘指数量化打分 Agent 需求文档

## 1. 简介

### 1.1 项目定位

大盘指数量化打分 Agent（以下简称 Agent）是一款基于 Python 技术栈的命令行工具，专注于对主流大盘指数进行量化打分，以"1-9 分"为评分标准（分数越低代表指数估值越便宜，越具备长期投资价值），通过终端 UI 展示打分结果，并支持生成 Markdown 格式投资参考报告。

### 1.2 目标用户

长期价值投资者、指数基金投资者。适配低频长期投资场景，每日查询 1-2 次即可满足投资决策需求。

### 1.3 核心价值

- **简化决策**：量化模型替代人工计算，一键输出标准化打分结果
- **客观透明**：固定模型确保打分一致性，因子权重和规则可配置
- **轻量运行**：终端 UI 无冗余操作，Python 环境即可运行

---

## 2. 功能清单

### 2.1 核心功能

| 功能 | 说明 | 详细设计 |
|------|------|---------|
| 指数量化打分 | 基于指数类型模板的 3 因子加权模型，自动计算 1-9 分 | [scoring/01-scoring-model.md](scoring/01-scoring-model.md) |
| 终端 UI 展示 | Textual 交互式界面，彩色表格 + 快捷键操作 | [architecture/01-architecture-design.md](architecture/01-architecture-design.md#6-ui--终端-ui-层) |
| LLM 报告解读 | LangChain Agent 基于打分结果生成自然语言投资解读 | [architecture/01-architecture-design.md](architecture/01-architecture-design.md#3-llm--llm-解读层) |
| 报告生成 | Markdown 格式标准化报告，含因子拆解和 LLM 解读 | [task-breakdown/01-task-breakdown.md](task-breakdown/01-task-breakdown.md#task-7markdown-报告生成) |

### 2.2 辅助功能

- **数据获取**：理杏仁 Open API（估值数据首选）/ AkShare（行情数据），手动触发，详见 [data-model/02-lixinger-api-integration.md](data-model/02-lixinger-api-integration.md)
- **异常处理**：API 重试、权重自动调整、兜底提示，详见各子文档

### 2.3 预设指数

| 指数名称 | 指数代码 | 市场 | 打分模板 |
|---------|---------|------|---------|
| 中证红利 | 000922 | CN | 红利型 (dividend) |
| 中证红利低波 | 930955 | CN | 红利型 (dividend) |
| 标普中国红利低波50 | 930735 | CN | 红利型 (dividend) |
| 国证价值100 | 399378 | CN | 价值型 (value) |
| 国证自由现金流 | 980092 | CN | 价值型 (value) |
| 纳指 | IXIC | US | 成长型 (growth) |
| 标普500 | SPX | US | 宽基型 (balanced) |

指数列表和模板绑定可在 config.yaml 中配置。

---

## 3. 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.10+ | - |
| 数据 | 理杏仁 Open API + AkShare + Pandas | 估值数据（PE/PB/股息率/分位点）+ 行情数据 |
| Agent | LangChain + langchain-openai | LLM Agent 构建，工具封装 |
| 终端 UI | Textual + Rich | 交互式终端界面 |
| 报告 | Jinja2 + Markdown | 报告模板化生成 |

**不使用**：SQLite（无缓存需求）、APScheduler（无定时任务）

---

## 4. 打分模型设计原则

打分模型的核心原则：**按指数类型选择最合适的因子和权重，同时保持可解释性。**

### 4.1 模板化设计

不同类型的指数使用不同的打分模板，每个模板定义自己的因子组合和权重：

| 模板 | 适用指数 | 因子1 | 因子2 | 因子3 |
|------|---------|-------|-------|-------|
| 红利型 (dividend) | 中证红利、中证红利低波、标普中国红利低波50 | 股息率分位 40% | PE 分位 35% | 价格位置 25% |
| 价值型 (value) | 国证价值100、国证自由现金流 | PE 分位 40% | PB 分位 30% | 股息率分位 30% |
| 成长型 (growth) | 纳指 | PE 分位 50% | 价格位置 35% | 股息率分位 15% |
| 宽基型 (balanced) | 标普500 | PE 分位 35% | 股息率分位 35% | 价格位置 30% |

详细设计理由和 Skill 关联 → [scoring/01-scoring-model.md](scoring/01-scoring-model.md)

### 4.2 通用规则

- **分位统计周期**：估值分位用 5 年，价格位置用 3 年
- **单因子打分**：≤20%→1分，20-40%→3分，40-60%→5分，60-80%→7分，>80%→9分
- **总分**：各因子分 × 对应权重，保留 2 位小数
- **数据缺失**：该因子权重按比例分配至其余因子
- 所有规则均可在 config.yaml 中调整

### 4.3 为什么是 5 档 1/3/5/7/9

- 5 档足够区分"便宜/中性/贵"，不过度拟合
- 奇数分档确保有明确的"中性"区间（5 分 = 40%-60%）
- 跳过偶数，强制每个区间有明确的"买入/观望/卖出"含义

---

## 5. V2 迭代规划

以下功能不在 V1 范围内，但架构已预留扩展点。

| 功能 | 说明 | 交互入口 |
|------|------|---------|
| 仓位配置建议 | 基于打分结果生成指数间配置比例 | 首页【A】按钮 |
| 自然语言问答 | 用户在详情面板输入问题，Agent 推理回答 | 详情面板输入框 |

V1 完成后优先实现仓位配置建议，再实现自然语言问答。

---

## 6. 文档索引

| 文档 | 路径 | 内容 |
|------|------|------|
| 打分模型 | [scoring/01-scoring-model.md](scoring/01-scoring-model.md) | 4 种打分模板定义、因子选择理由、Skill 关联、计算规则 |
| 架构设计 | [architecture/01-architecture-design.md](architecture/01-architecture-design.md) | 6 层模块划分、数据流、目录结构、关键设计决策 |
| 数据模型 | [data-model/01-data-model.md](data-model/01-data-model.md) | 核心 dataclass 定义、字段规范、模块间数据流契约 |
| 理杏仁接入 | [data-model/02-lixinger-api-integration.md](data-model/02-lixinger-api-integration.md) | 理杏仁 API 接口规范、metricsList 格式、接入方案 |
| 工程基建 | [engineering/01-engineering-setup.md](engineering/01-engineering-setup.md) | pyproject.toml、依赖清单、config.yaml 模板、开发工具配置 |
| 任务拆解 | [task-breakdown/01-task-breakdown.md](task-breakdown/01-task-breakdown.md) | 9 个可执行任务、依赖关系、验收标准 |
