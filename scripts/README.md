# scripts/ — 开发辅助脚本

开发阶段的探索、调试和数据验证脚本，不属于项目核心代码。运行前请确保已安装项目依赖（`pip install -e ".[dev]"`），并根据需要在 `.env` 中配置相应 Token。

---

## 业务脚本

| 脚本 | 用途 |
|------|------|
| [run_report.py](#run_report) | 一键运行完整流程：数据拉取 → 打分 → LLM 解读 → 生成报告 |
| [preview_data.py](#preview_data) | 预览各指数的行情和估值数据，快速确认数据源是否正常 |
| [calc_score_from_csv.py](#calc_score_from_csv) | 用理杏仁导出的 CSV 离线计算红利低波指数打分，验证打分逻辑 |

## 连通性/数据源测试脚本

| 脚本 | 依赖 Token | 测试目标 |
|------|-----------|---------|
| [test_lixinger_api.py](#test_lixinger_api) | `LIXINGER_TOKEN` | 理杏仁 Open API：指数基本信息、基本面数据、分位点 |
| [test_llm_connectivity.py](#test_llm_connectivity) | `INDEX_SCORE_LLM_API_KEY` | DeepSeek API 连通性 |
| [test_fetch_apis.py](#test_fetch_apis) | 无 | AkShare 各行情/估值接口逐个测试，为每个指数找最优数据源 |
| [test_valuation_apis.py](#test_valuation_apis) | 无 | 中证红利的行情+PE+PB+股息率各接口综合可用性 |
| [test_etf.py](#test_etf) | 无 | ETF 代码（如 515450）在各行情/估值接口的数据覆盖 |
| [test_tushare_index.py](#test_tushare_index) | `TUSHARE_TOKEN` | Tushare MCP：上证指数基础数据接口 |
| [test_tushare_mcp.py](#test_tushare_mcp) | `TUSHARE_TOKEN` | Tushare MCP：指数估值数据接口 |
| [test_tushare_valuation.py](#test_tushare_valuation) | `TUSHARE_TOKEN` | Tushare：index_dailybasic / fund_daily / daily_basic |
| [test_index_dailybasic_all.py](#test_index_dailybasic_all) | `TUSHARE_TOKEN` | Tushare MCP：批量测试所有目标指数的 index_dailybasic 覆盖率 |

---

## 脚本说明

<a id="run_report"></a>
### run_report.py

一键运行完整流程，等价于 `python main.py --report`，适合快速验证或定时任务。

```bash
python scripts/run_report.py
```

流程：加载 config.yaml → 拉取 AkShare 行情 + 理杏仁估值 → 计算打分 → 调用 LLM 生成解读 → 输出 Markdown 报告到 `report/` 目录。

<a id="preview_data"></a>
### preview_data.py

逐个预览 config.yaml 中配置的指数的行情和估值原始数据，用于快速排查数据源问题。

```bash
python scripts/preview_data.py
```

输出：每个指数最近 5 条行情（OHLCV）+ 最新估值（PE/PB/股息率/分位点）。

<a id="calc_score_from_csv.py"></a>
### calc_score_from_csv.py

用理杏仁网页手动导出的 CSV 数据（`data/` 目录下）离线计算红利低波指数的综合打分。用于验证打分逻辑是否与理杏仁网页端一致。

```bash
python scripts/calc_score_from_csv.py
```

所需 CSV 文件（放在 `data/` 目录）：
- `红利低波100_股息率_市值加权_上市以来_*.csv`
- `红利低波100_PE-TTM_市值加权_上市以来_*.csv`
- `红利低波100_PB_市值加权_上市以来_*.csv`

<a id="test_lixinger_api"></a>
### test_lixinger_api.py

测试理杏仁 Open API 的连通性和数据格式。逐个测试指数信息查询、基本面数据查询，验证 metricsList 格式和分位点返回值。

```bash
python scripts/test_lixinger_api.py
```

<a id="test_llm_connectivity"></a>
### test_llm_connectivity.py

测试 DeepSeek API 连通性，发送一条简单消息验证 Key 和网络是否正常。

```bash
python scripts/test_llm_connectivity.py
```

<a id="test_fetch_apis"></a>
### test_fetch_apis.py

逐个测试 AkShare 提供的各指数行情和估值接口，为 config.yaml 中每个指数找出最优数据源。包括新浪、腾讯、东方财富等多个后端。

```bash
python scripts/test_fetch_apis.py
```

<a id="test_valuation_apis"></a>
### test_valuation_apis.py

专门测试中证红利（000922）的各数据接口综合可用性：行情+PE 一体接口、理杏仁 PB、csindex 实时 PE+股息率，并尝试合并出完整的估值时间序列。

```bash
python scripts/test_valuation_apis.py
```

<a id="test_etf"></a>
### test_etf.py

测试 ETF 代码（515450、159201）在各行情接口和中证估值接口中的数据覆盖情况，判断 ETF 代码能否替代指数代码用于数据拉取。

```bash
python scripts/test_etf.py
```

<a id="test_tushare_index"></a>
### test_tushare_index.py

通过 Tushare Pro MCP 服务测试上证指数（000001.SH）的基础数据接口，包括指数基本信息、日线行情、每日指标等。

```bash
python scripts/test_tushare_index.py
```

<a id="test_tushare_mcp"></a>
### test_tushare_mcp.py

通过 Tushare Pro MCP 服务测试指数估值数据接口，验证 PE/PB/股息率等字段的返回格式和覆盖率。

```bash
python scripts/test_tushare_mcp.py
```

<a id="test_tushare_valuation"></a>
### test_tushare_valuation.py

测试 Tushare 的三个估值相关接口：`index_dailybasic`（指数 PE/PB）、`fund_daily`（ETF 行情）、`daily_basic`（股票 PE/PB/股息率），评估各接口对目标指数的覆盖能力。

```bash
python scripts/test_tushare_valuation.py
```

<a id="test_index_dailybasic_all"></a>
### test_index_dailybasic_all.py

通过 Tushare MCP 批量测试所有目标指数（约 20 个）的 `index_dailybasic` 数据覆盖情况，快速判断哪些指数有 PE/PB 数据、哪些缺失。

```bash
python scripts/test_index_dailybasic_all.py
```
