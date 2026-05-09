# 数据缺口分析与 Tushare Pro 迁移指南

## 输入

- 数据模型：`01-data-model.md`
- 打分模型：`../scoring/01-scoring-model.md`
- 配置文件：`../../../config.yaml`

## 输出

- 当前数据缺口的完整记录
- 降级策略（方案1）的设计说明
- Tushare Pro 接入后的迁移方案

## 验收标准（DoD）

- [x] 记录了每个指数的因子覆盖情况
- [x] 说明了降级打分策略的逻辑
- [x] 提供了 Tushare 接入后的完整代码改动指引

---

## 1. 背景

打分模型设计了 4 种模板（红利型、价值型、成长型、宽基型），每个模板需要 3 个因子。完整数据需求：

| 因子 | 统计周期 | 数据字段 |
|------|---------|---------|
| PE 百分位 | 近 5 年 | pe_percentile_5y |
| PB 百分位 | 近 5 年 | pb_percentile_5y |
| 股息率百分位 | 近 5 年 | dividend_yield_percentile_5y |
| 价格位置 | 近 3 年 | price_position_percentile_3y |

其中价格位置（3 年历史行情）可通过 AkShare 稳定获取。**缺口在于 PE/PB/股息率的 5 年历史估值数据。**

---

## 2. AkShare 估值接口调研结果

### 2.1 已测试的接口

| 接口 | PE | PB | 股息率 | 覆盖范围 | 历史深度 | 状态 |
|------|----|----|--------|---------|---------|------|
| `stock_zh_index_hist_csindex` | ✅ | ❌ | ❌ | 仅中证系列（000922、930955 可用；399371、980092 报错） | 5 年 | **可用** |
| `stock_index_pe_lg` (理杏仁) | ✅ | ❌ | ❌ | 仅沪深300等少数大指数，我们的指数全部 KeyError | ~20 年 | 不可用 |
| `stock_index_pb_lg` (理杏仁) | ❌ | ✅ | ❌ | 同上 | ~20 年 | 不可用 |
| `stock_zh_index_value_csindex` | ✅ | ❌ | ✅ | 同 hist_csindex | **仅 20 条快照** | 数据量不足 |
| ~~`index_value_hist_funddb`~~ (韭圈儿) | ~~✅~~ | ~~✅~~ | ~~✅~~ | — | — | **已从 AkShare 移除** |

`index_value_hist_funddb` 是最佳候选接口（PE+PB+股息率全覆盖、5 年+历史），但上游数据源（韭圈儿）失效后 AkShare 官方已将其移除。GitHub Issue [#5557](https://github.com/akfamily/akshare/issues/5557)，维护者确认"已移除"。

### 2.2 每个指数的因子覆盖现状

| 指数 | 代码 | 行情(3y) | PE(5y) | PB(5y) | 股息率(5y) | 可用因子数 | 需要因子数 |
|------|------|----------|--------|--------|-----------|-----------|-----------|
| 中证红利 | 000922 | ✅ | ✅ csindex | ❌ | ❌ | 2 | 3 |
| 中证红利低波 | 930955 | ✅ | ✅ csindex | ❌ | ❌ | 2 | 3 |
| 标普中国红利低波50ETF | 515450 | ✅ | ❌ | ❌ | ❌ | 1 | 3 |
| 国证价值100 | 399371 | ✅ | ❌ | ❌ | ❌ | 1 | 3 |
| 国证自由现金流ETF | 159201 | ✅ | ❌ | ❌ | ❌ | 1 | 3 |
| 纳指 | IXIC | ✅ | ❌ | ❌ | ❌ | 1 | 3 |
| 标普500 | SPX | ✅ | ❌ | ❌ | ❌ | 1 | 3 |

**结论：没有任何一个指数拥有完整的三因子估值数据。**

---

## 3. 降级策略（方案1：先跑通 MVP）

### 3.1 设计原则

- 打分模型的权重自动调整逻辑已内置（数据缺失时权重按比例分配至其余因子，见打分模型 3.3 节）
- 不修改打分模板定义，只在数据层做降级
- 终端需明确提示用户当前数据的覆盖情况

### 3.2 各指数降级后的实际打分因子

| 指数 | 模板 | 原始 3 因子 | 降级后可用因子 | 实际权重分配 |
|------|------|-----------|--------------|-------------|
| 中证红利 | 红利型 | 股息率 40% + PE 35% + 价格 25% | PE + 价格 | PE 58.3% + 价格 41.7% |
| 中证红利低波 | 红利型 | 同上 | PE + 价格 | PE 58.3% + 价格 41.7% |
| 标普红利低波ETF | 红利型 | 同上 | 价格 | 价格 100%（仅一因子，可信度低） |
| 国证价值100 | 价值型 | PE 40% + PB 30% + 股息率 30% | 价格 | 价格 100%（仅一因子，可信度低） |
| 自由现金流ETF | 价值型 | 同上 | 价格 | 价格 100%（仅一因子，可信度低） |
| 纳指 | 成长型 | PE 50% + 价格 35% + 股息率 15% | 价格 | 价格 100%（仅一因子，可信度低） |
| 标普500 | 宽基型 | PE 35% + 股息率 35% + 价格 30% | 价格 | 价格 100%（仅一因子，可信度低） |

### 3.3 降级策略在 fetcher 中的实现

当前 `fetcher.py` 中 `fetch_valuation()` 的返回值已预留了所有估值字段，缺失字段填充 `None`。打分模块根据 `None` 值自动跳过该因子并调整权重，无需额外代码。

关键约定：

```python
# fetcher.py 返回的 IndexValuation 中，缺失字段必须显式设置为 None
# 打分模块通过 pe is None / pb is None / dividend_yield is None 判断是否跳过
```

### 3.4 数据来源映射（降级方案）

```python
# 当前 fetcher.py 中实际使用的数据源
VALUATION_SOURCES = {
    "000922": {"pe": "csindex", "pb": None, "dividend_yield": None},
    "930955": {"pe": "csindex", "pb": None, "dividend_yield": None},
    "515450": {"pe": None, "pb": None, "dividend_yield": None},
    "399371": {"pe": None, "pb": None, "dividend_yield": None},
    "159201": {"pe": None, "pb": None, "dividend_yield": None},
    "IXIC":   {"pe": None, "pb": None, "dividend_yield": None},
    "SPX":    {"pe": None, "pb": None, "dividend_yield": None},
}
```

---

## 4. Tushare Pro 接入方案（后续迁移）

> **触发条件**：用户购买 Tushare Pro token 后，按此章节指引补充缺失因子。

### 4.1 Tushare 接口选择

| 接口 | 提供字段 | 覆盖范围 | 调用限制 |
|------|---------|---------|---------|
| `index_dailybasic` | PE(TTM)、PB(LF)、股息率 | 全系列 A 股指数（中证、国证等） | 基础档 200 次/分钟 |
| `fund_daily` | PE(TTM)、PB(LF)、股息率 | ETF（场内基金） | 基础档 200 次/分钟 |

- A 股指数（000922、930955、399371）→ `index_dailybasic`
- ETF（515450、159201）→ `fund_daily`
- 美股（IXIC、SPX）→ Tushare 不覆盖，继续用价格位置

### 4.2 接入步骤

#### 步骤 1：配置 token

在 `config.yaml` 中新增 Tushare 配置：

```yaml
tushare:
  token: "YOUR_TUSHARE_PRO_TOKEN"  # 用户购买后填入
```

#### 步骤 2：扩展 IndexInfo 模型

`src/index_score/config/models.py` 中新增字段（可选）：

```python
@dataclass
class IndexInfo:
    code: str
    name: str
    market: str
    template: str
    tushare_code: str = ""       # 新增：Tushare 专用代码，如 "000922.SH"
    is_etf: bool = False         # 新增：是否为 ETF，决定调用 fund_daily 还是 index_dailybasic
```

`config.yaml` 中对应修改：

```yaml
indexes:
  - code: "000922"
    name: "中证红利"
    market: "CN"
    template: "dividend"
    tushare_code: "000922.SH"    # 新增
  - code: "515450"
    name: "标普中国红利低波50ETF"
    market: "CN"
    template: "dividend"
    is_etf: true                 # 新增
```

#### 步骤 3：实现 Tushare 估值拉取

在 `src/index_score/data/fetcher.py` 中新增：

```python
import tushare as ts

def _init_tushare(token: str) -> ts.pro_api:
    return ts.pro_api(token)

def fetch_valuation_tushare(
    pro: ts.pro_api,
    ts_code: str,
    start_date: str,
    end_date: str,
    *,
    is_etf: bool = False,
) -> pd.DataFrame:
    """从 Tushare 拉取 5 年估值历史。

    返回 DataFrame，列：date, pe_ttm, pb, dividend_yield
    """
    if is_etf:
        df = pro.fund_daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields="trade_date,pe_ttm,pb,dv_ratio",
        )
        df = df.rename(columns={
            "trade_date": "date",
            "dv_ratio": "dividend_yield",
        })
    else:
        df = pro.index_dailybasic(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields="trade_date,pe_ttm,pb,dv_ratio",
        )
        df = df.rename(columns={
            "trade_date": "date",
            "dv_ratio": "dividend_yield",
        })
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)
```

#### 步骤 4：集成到 fetch_valuation 流程

修改 `fetcher.py` 中的估值获取逻辑，加入 Tushare 作为补充数据源：

```python
def fetch_valuation(
    index_info: IndexInfo,
    years: int = 5,
) -> IndexValuation:
    code = index_info.code
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y%m%d")

    pe, pb, dividend_yield = None, None, None

    # 1. 尝试 AkShare csindex（仅中证系列有 PE）
    if index_info.market == "CN" and not index_info.is_etf:
        pe = _try_fetch_pe_from_csindex(code)

    # 2. 尝试 Tushare 补充缺失字段
    tushare_token = config.tushare.token if config.tushare else None
    if tushare_token and index_info.tushare_code:
        pro = _init_tushare(tushare_token)
        df = fetch_valuation_tushare(
            pro,
            index_info.tushare_code,
            start_date,
            end_date,
            is_etf=index_info.is_etf,
        )
        if not df.empty:
            latest = df.iloc[-1]
            if pe is None:
                pe = latest.get("pe_ttm")
            if pb is None:
                pb = latest.get("pb")
            if dividend_yield is None:
                dividend_yield = latest.get("dividend_yield")

    # 3. 计算百分位（有历史数据才计算）
    # ... percentile 计算逻辑 ...

    return IndexValuation(
        code=code,
        pe_ttm=pe,
        pe_percentile_5y=pe_pct,
        pb_lf=pb,
        pb_percentile_5y=pb_pct,
        dividend_yield=dividend_yield,
        dividend_yield_percentile_5y=dy_pct,
    )
```

#### 步骤 5：更新测试

在 `tests/test_data.py` 中补充 Tushare mock 测试：

```python
class TestFetchValuationTushare:
    def test_tushare_fills_missing_fields(self):
        """Tushare 补充 AkShare 缺失的 PB 和股息率。"""
        # Mock AkShare 返回只有 PE
        # Mock Tushare 返回 PE + PB + 股息率
        # 断言最终结果三个字段都有值

    def test_tushare_etf_uses_fund_daily(self):
        """ETF 调用 fund_daily 而非 index_dailybasic。"""
        # Mock is_etf=True
        # 断言调用的是 pro.fund_daily

    def test_tushare_failure_graceful(self):
        """Tushare 失败不影响已有数据。"""
        # Mock Tushare 抛异常
        # 断言 AkShare 获取的 PE 仍然保留
```

### 4.3 接入后数据覆盖预期

| 指数 | PE | PB | 股息率 | 数据来源 |
|------|----|----|--------|---------|
| 中证红利 000922 | ✅ | ✅ | ✅ | csindex PE + Tushare PB/股息率 |
| 中证红利低波 930955 | ✅ | ✅ | ✅ | csindex PE + Tushare PB/股息率 |
| 标普红利低波ETF 515450 | ✅ | ✅ | ✅ | Tushare fund_daily（全部） |
| 国证价值100 399371 | ✅ | ✅ | ✅ | Tushare index_dailybasic（全部） |
| 自由现金流ETF 159201 | ✅ | ✅ | ✅ | Tushare fund_daily（全部） |
| 纳指 IXIC | ❌ | ❌ | ❌ | 仅价格位置（Tushare 不覆盖美股） |
| 标普500 SPX | ❌ | ❌ | ❌ | 仅价格位置（Tushare 不覆盖美股） |

接入后，5 个 A 股/ETF 指数将拥有完整的三因子数据，打分模型可发挥全部效果。美股指数仍依赖价格位置单因子。

---

## 5. 快速检查清单（给 AI 或开发者）

当用户提供 Tushare Pro token 后，按以下顺序操作：

- [ ] `config.yaml` 中新增 `tushare.token` 配置
- [ ] `config.yaml` 各指数补充 `tushare_code` 和 `is_etf` 字段
- [ ] `src/index_score/config/models.py` 中 `IndexInfo` 新增 `tushare_code` 和 `is_etf` 字段
- [ ] `src/index_score/config/loader.py` 解析新字段
- [ ] `pip install tushare`，加入 `pyproject.toml` 的 dependencies
- [ ] `src/index_score/data/fetcher.py` 中实现 `fetch_valuation_tushare()`
- [ ] `fetch_valuation()` 中集成 Tushare 作为补充数据源
- [ ] `tests/test_data.py` 中补充 Tushare mock 测试
- [ ] `python scripts/test_valuation_apis.py` 验证实际数据拉取
- [ ] 确认所有 7 个指数的因子覆盖率表（见第 4.3 节）达到预期
