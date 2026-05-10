# 理杏仁 Open API 接入方案

## 输入

- 数据模型：`01-data-model.md`
- 打分模型：`../scoring/01-scoring-model.md`
- 配置文件：`../../../config.yaml`

## 输出

- 理杏仁 API 接口规范
- 数据模型映射
- fetcher.py 重构指引
- 已测试的接口及返回数据示例

## 验收标准（DoD）

- [x] 记录了理杏仁 API 接口规范和参数格式
- [x] 说明了 metricsList 的完整格式
- [x] 提供了接口调用的返回数据示例
- [ ] 实现 `src/index_score/data/lixinger.py`
- [ ] 重写 `fetcher.py` 中的 `fetch_valuation()`

---

## 1. 背景

经过 AkShare / Tushare / 理杏仁三个数据源的全面测试，理杏仁 Open API 是唯一能完美支持本项目的数据源：

| 数据源 | PE | PB | 股息率 | 分位点 | 覆盖范围 | 状态 |
|--------|:--:|:--:|:------:|:------:|---------|------|
| AkShare csindex | ✅ | ❌ | ❌ | ❌ | 仅 2 个中证指数 | 不可用 |
| AkShare funddb | — | — | — | — | 已移除 | 不可用 |
| Tushare index_dailybasic | ✅ | ✅ | ✅ | ❌ | 仅 5 个宽基指数 | 不可用 |
| **理杏仁 API** | ✅ | ✅ | ✅ | ✅ | 所有 A 股指数 | **确定使用** |

---

## 2. API 接口规范

### 2.1 指数基本信息

```
POST https://open.lixinger.com/api/cn/index
```

| 参数 | 必选 | 类型 | 说明 |
|------|:----:|------|------|
| token | Yes | String | 用户专属 Token |
| stockCodes | No | Array | 指数代码数组，如 `["930955"]`，默认返回所有指数 |

返回字段：name, stockCode, areaCode, market, source, series, launchDate, rebalancingFrequency, calculationMethod, fsTableType

### 2.2 指数基本面数据（核心接口）

```
POST https://open.lixinger.com/api/cn/index/fundamental
```

| 参数 | 必选 | 类型 | 说明 |
|------|:----:|------|------|
| token | Yes | String | 用户专属 Token |
| stockCodes | Yes | Array | 指数代码数组，长度 >= 1 且 <= 100 |
| date | No | String | 指定日期，格式 `YYYY-MM-DD` |
| startDate | No | String | 起始日期（与 date 二选一） |
| endDate | No | String | 结束日期，默认上周一 |
| limit | No | Number | 返回最近数据数量（仅时间范围模式生效） |
| metricsList | Yes | Array | 指标数组，详见下方 |

### 2.3 metricsList 格式

**三种格式**：

1. **`[metricsName].[granularity].[metricsType].[statisticsDataType]`** — 估值统计指标
2. **`[metricsName].[metricsType]`** — 估值当前值（市值加权/等权）
3. **`[metricsName]`** — 其他指标（收盘点位、市值、成交量等）

**metricsName**：

| 名称 | 代码 |
|------|------|
| PE-TTM | `pe_ttm` |
| PB | `pb` |
| PS-TTM | `ps_ttm` |
| 股息率 | `dyr` |
| 收盘点位 | `cp` |
| 全收益收盘点位 | `r_cp` |
| 市值 | `mc` |
| 涨跌幅 | `cpc` |
| 成交量 | `tv` |
| 成交金额 | `ta` |
| 换手率 | `to_r` |

**granularity**（统计窗口）：

| 名称 | 代码 |
|------|------|
| 上市以来 | `fs` |
| 20年 | `y20` |
| 10年 | `y10` |
| 5年 | `y5` |
| 3年 | `y3` |
| 1年 | `y1` |

**metricsType**（加权方式）：

| 名称 | 代码 |
|------|------|
| 市值加权 | `mcw` |
| 等权 | `ew` |
| 正数等权 | `ewpvo` |
| 平均值 | `avg` |
| 中位数 | `median` |

**statisticsDataType**（统计值类型）：

| 名称 | 代码 | 说明 |
|------|------|------|
| 当前值 | `cv` | 当前实际值 |
| 分位点% | `cvpos` | 当前值在历史中的百分位（0~1） |
| 最小值 | `minv` | 统计窗口内最小值 |
| 最大值 | `maxv` | 统计窗口内最大值 |
| 最大正值 | `maxpv` | 统计窗口内最大正值 |
| 50%分位点值 | `q5v` | 中位数的绝对值 |
| 80%分位点值 | `q8v` | 80%分位的绝对值 |
| 20%分位点值 | `q2v` | 20%分位的绝对值 |
| 平均值 | `avgv` | 统计窗口内平均值 |

---

## 3. 本项目所需的 metricsList

### 3.1 打分所需的指标

| 打分因子 | metricsList 参数 | 说明 |
|---------|-----------------|------|
| PE-TTM 当前值 | `pe_ttm.mcw` | 市值加权 PE-TTM |
| PE 5年分位点 | `pe_ttm.y5.mcw.cvpos` | PE 在近5年中的百分位 |
| PB 当前值 | `pb.mcw` | 市值加权 PB |
| PB 5年分位点 | `pb.y5.mcw.cvpos` | PB 在近5年中的百分位 |
| 股息率当前值 | `dyr.mcw` | 市值加权股息率 |
| 股息率5年分位点 | `dyr.y5.mcw.cvpos` | 股息率在近5年中的百分位 |
| 收盘点位 | `cp` | 当前收盘点位 |
| 全收益收盘点位 | `r_cp` | 含分红再投资的收盘点位 |

### 3.2 完整请求示例

```python
import requests

resp = requests.post(
    "https://open.lixinger.com/api/cn/index/fundamental",
    json={
        "token": "YOUR_TOKEN",
        "stockCodes": ["930955", "000300"],
        "date": "2026-05-08",
        "metricsList": [
            "cp",
            "r_cp",
            "mc",
            "pe_ttm.mcw",
            "pb.mcw",
            "dyr.mcw",
            "pe_ttm.y5.mcw.cvpos",
            "pb.y5.mcw.cvpos",
            "dyr.y5.mcw.cvpos",
        ],
    },
    timeout=30,
)
data = resp.json()
```

### 3.3 返回数据示例

```json
{
    "code": 1,
    "data": [
        {
            "stockCode": "930955",
            "date": "2026-05-08T00:00:00+08:00",
            "cp": 11922.56,
            "r_cp": 23114.55,
            "mc": 21832280367329.176,
            "pe_ttm.mcw": 9.12882814666838,
            "pb.mcw": 0.88340464477346,
            "dyr.mcw": 0.04431856750112664,
            "pe_ttm.y5.mcw.cvpos": 0.9049586776859504,
            "pb.y5.mcw.cvpos": 0.8743801652892562,
            "dyr.y5.mcw.cvpos": 0.09338842975206611
        },
        {
            "stockCode": "000300",
            "date": "2026-05-08T00:00:00+08:00",
            "cp": 4871.91,
            "r_cp": 6298.47,
            "mc": 62712081596623.16,
            "pe_ttm.mcw": 14.74294620957601,
            "pb.mcw": 1.4643755082464266,
            "dyr.mcw": 0.026923210157556996,
            "pe_ttm.y5.mcw.cvpos": 0.9942148760330579,
            "pb.y5.mcw.cvpos": 0.6818181818181818,
            "dyr.y5.mcw.cvpos": 0.1931122448979592
        }
    ]
}
```

### 3.4 分位点详细统计示例

请求 `pe_ttm.y5.mcw.cv` / `pe_ttm.y5.mcw.cvpos` / `pe_ttm.y5.mcw.minv` / `pe_ttm.y5.mcw.maxv` / `pe_ttm.y5.mcw.q2v` / `pe_ttm.y5.mcw.q5v` / `pe_ttm.y5.mcw.q8v` / `pe_ttm.y5.mcw.avgv` 返回：

```
PE-TTM (5年, 市值加权):
  当前值: 9.1288  |  分位点: 0.9050 (90.5%)
  最小值: 5.0805  |  最大值: 9.9872
  20%分位: 5.8362 |  50%分位: 6.3162 |  80%分位: 8.2264
  平均值: 6.8765

PB (5年, 市值加权):
  当前值: 0.8834  |  分位点: 0.8744 (87.4%)
  最小值: 0.5792  |  最大值: 1.0390
  20%分位: 0.6451 |  50%分位: 0.6860 |  80%分位: 0.8423
  平均值: 0.7386

股息率 (5年, 市值加权):
  当前值: 0.0443  |  分位点: 0.0934 (9.3%)
  最小值: 0.0421  |  最大值: 0.0683
  20%分位: 0.0469 |  50%分位: 0.0535 |  80%分位: 0.0588
  平均值: 0.0533
```

### 3.5 时间范围查询示例

```python
resp = requests.post(
    "https://open.lixinger.com/api/cn/index/fundamental",
    json={
        "token": "YOUR_TOKEN",
        "stockCodes": ["930955"],
        "startDate": "2024-01-01",
        "endDate": "2026-05-08",
        "metricsList": ["cp", "pe_ttm.mcw", "pb.mcw", "dyr.mcw"],
        "limit": 5,
    },
)
```

返回 5 条日频记录，每条包含 date + 请求的指标值。

---

## 4. 数据模型映射

### 4.1 IndexValuation 字段映射

| IndexValuation 字段 | 理杏仁 API metricsList | 值说明 |
|--------------------|----------------------|--------|
| `pe_ttm` | `pe_ttm.mcw` | 直接使用 |
| `pe_percentile_5y` | `pe_ttm.y5.mcw.cvpos` | 直接使用（0~1） |
| `pb_lf` | `pb.mcw` | 直接使用 |
| `pb_percentile_5y` | `pb.y5.mcw.cvpos` | 直接使用（0~1） |
| `dividend_yield` | `dyr.mcw` | 直接使用（0.04 = 4%） |
| `dividend_yield_percentile_5y` | `dyr.y5.mcw.cvpos` | 直接使用（0~1） |

**关键优势**：理杏仁 API 直接返回分位点，无需自己从历史数据计算百分位。

### 4.2 IndexInfo 模型扩展

需新增 `lixinger_code` 字段，用于理杏仁 API 的 stockCodes 参数：

```python
@dataclass
class IndexInfo:
    code: str
    name: str
    market: str
    template: str
    lixinger_code: str = ""  # 理杏仁指数代码，如 "930955"
```

config.yaml 对应：

```yaml
indexes:
  - code: "930955"
    name: "红利低波100"
    market: "CN"
    template: "dividend"
    lixinger_code: "930955"
```

### 4.3 新增 LixingerConfig

```python
@dataclass
class LixingerConfig:
    token: str
    base_url: str = "https://open.lixinger.com/api"
    timeout: int = 30
```

---

## 5. 已测试的指数

| 代码 | 名称 | 系列 | 加权方式 | 来源 |
|------|------|------|---------|------|
| 930955 | 红利低波100 | strategy | — | csi |
| 399967 | 中证军工 | thematic | grading_weighted | csi |
| 000015 | 红利指数 | strategy | dividend_grading | csi |
| 000300 | 沪深300 | size | grading_weighted | csi |
| 000905 | 中证500 | size | grading_weighted | csi |

**批量查询测试**：5 个指数一次请求全部返回 PE/PB/股息率 + 分位点，耗时 < 1 秒。

**历史数据测试**：时间范围查询返回日频数据，limit 参数控制返回条数。

---

## 6. 代码实现指引

### 6.1 新建 `src/index_score/data/lixinger.py`

```python
"""理杏仁 Open API 客户端。"""

from __future__ import annotations

import logging
import requests
from dataclasses import dataclass

logger = logging.getLogger(__name__)

BASE_URL = "https://open.lixinger.com/api"


class LixingerError(Exception):
    """理杏仁 API 调用失败。"""


@dataclass
class LixingerClient:
    token: str
    base_url: str = BASE_URL
    timeout: int = 30

    def fetch_fundamental(
        self,
        stock_codes: list[str],
        date: str | None = None,
        metrics_list: list[str] | None = None,
    ) -> list[dict]:
        """查询指数基本面数据。"""
        if metrics_list is None:
            metrics_list = [
                "cp", "r_cp", "mc",
                "pe_ttm.mcw", "pb.mcw", "dyr.mcw",
                "pe_ttm.y5.mcw.cvpos", "pb.y5.mcw.cvpos", "dyr.y5.mcw.cvpos",
            ]
        body = {
            "token": self.token,
            "stockCodes": stock_codes,
            "metricsList": metrics_list,
        }
        if date:
            body["date"] = date
        return self._post("/cn/index/fundamental", body)

    def _post(self, path: str, body: dict) -> list[dict]:
        url = f"{self.base_url}{path}"
        resp = requests.post(url, json=body, timeout=self.timeout)
        if resp.status_code != 200:
            raise LixingerError(f"HTTP {resp.status_code}: {resp.text[:500]}")
        result = resp.json()
        if isinstance(result, dict) and "data" in result:
            if result.get("code") != 1:
                raise LixingerError(
                    f"API error: code={result.get('code')}, message={result.get('message')}"
                )
            return result["data"]
        return result
```

### 6.2 重写 `fetcher.py` 中的 `fetch_valuation()`

```python
def fetch_valuation(
    index_info: IndexInfo,
    lixinger_client: LixingerClient,
    date: str | None = None,
) -> IndexValuation:
    """从理杏仁 API 拉取估值数据。"""
    code = index_info.lixinger_code or index_info.code
    if not code or index_info.market != "CN":
        return IndexValuation(code=index_info.code, date=date or "")

    data = lixinger_client.fetch_fundamental([code], date=date)
    if not data:
        return IndexValuation(code=index_info.code, date=date or "")

    item = data[0]
    return IndexValuation(
        code=index_info.code,
        date=item.get("date", "")[:10],
        pe_ttm=item.get("pe_ttm.mcw"),
        pe_percentile_5y=item.get("pe_ttm.y5.mcw.cvpos"),
        pb_lf=item.get("pb.mcw"),
        pb_percentile_5y=item.get("pb.y5.mcw.cvpos"),
        dividend_yield=item.get("dyr.mcw"),
        dividend_yield_percentile_5y=item.get("dyr.y5.mcw.cvpos"),
    )
```

### 6.3 fallback.py 简化

```python
def fetch_all(
    index_info: IndexInfo,
    lixinger_client: LixingerClient,
    *,
    price_years: int = 3,
) -> FetchResult:
    """拉取行情（AkShare）+ 估值（理杏仁），自动重试 + 清洗。"""
    raw_quotes = fetch_with_retry(fetch_price_history, index_info, years=price_years)
    quotes = [clean_quote(q) for q in raw_quotes]

    raw_valuation = _try_fetch_valuation(index_info, lixinger_client)
    valuation = clean_valuation(raw_valuation)

    return FetchResult(quotes=quotes, valuation=valuation)
```

---

## 7. 环境配置

`.env` 文件：

```
LIXINGER_TOKEN=your_token_here
```

`config.yaml` 新增：

```yaml
lixinger:
  token_env: "LIXINGER_TOKEN"  # 从环境变量读取
  base_url: "https://open.lixinger.com/api"
  timeout: 30
```

---

## 8. 错误处理

| 场景 | 处理方式 |
|------|---------|
| HTTP 400 | 解析错误信息，记录日志，返回空估值 |
| HTTP 401/403 | Token 无效，抛出 LixingerError |
| 网络超时 | 重试 3 次，间隔 3 秒 |
| 返回数据为空 | 返回空 IndexValuation（所有字段 None） |
| 某指标值为 null | 保留 None，打分模块自动跳过 |
