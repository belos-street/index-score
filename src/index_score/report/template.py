"""Jinja2 报告模板定义。"""

from __future__ import annotations

from jinja2 import Template

REPORT_TEMPLATE = Template("""\
# 大盘指数量化打分报告

> 生成日期：{{ generated_at }} | 数据来源：理杏仁 API / AkShare

## 摘要

| 指标 | 值 |
|------|---|
| 打分指数数量 | {{ summary.total_count }} |
| 平均分 | {{ summary.avg_score_str }} |
| 最低分指数 | {{ summary.cheapest_line }} |
| 最高分指数 | {{ summary.most_expensive_line }} |
| 整体水平 | {{ summary.overall_level }} |

## 打分明细

{{ score_table }}

## 指数详细分析

{% for item in analyses %}
### {{ loop.index }}. {{ item.title_line }}

**估值概况**：{{ item.valuation_summary }}

**LLM 解读**：

{{ item.interpretation }}

---

{% endfor %}
## 数据来源与声明

- 数据更新时间：{{ generated_at }}
- 数据来源：理杏仁 API（估值分位）/ AkShare（历史行情）
- 本报告由量化模型自动生成，仅供参考，不构成投资建议
""")
