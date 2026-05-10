# Textual 终端界面设计 (Task 8)

## 需求来源

- 任务列表：`todo.md` L161-175
- 架构设计：`01-architecture-design.md` — ui 模块

## 设计方案

采用 **单屏表格 + Modal 弹窗详情** 方案（方案 A）。

主界面全屏 DataTable + 底部 ActionBar，按 Enter 弹出 ModalScreen 全屏展示因子详情和 LLM 解读。

**备选方案**：
- 方案 B：双面板布局（左侧表格 + 右侧详情），终端宽度有限，详情可能显示不全
- 方案 C：多 Screen 导航（独立 HomeScreen / DetailScreen），比 Modal 更重量级

## 架构与数据流

```
main.py (CLI 入口)
  └── IndexScoreApp (Textual App)
        ├── Header widget (标题区)
        ├── ScoreTable widget (DataTable + 颜色规则)
        ├── ActionBar widget (底部快捷键栏)
        │
        ├── on_mount → 启动后台 Worker 拉取数据
        │     fetch_data_worker() → data.fallback.fetch_all
        │                          → scoring.calculator
        │                          → llm.agent.interpret_direct (逐个)
        │     完成后 → post_message(DataReady) → UI 线程更新表格
        │
        ├── R key → 重新启动 fetch_data_worker (异步，不阻塞 UI)
        │     刷新期间表格显示 "正在刷新..." Footer 提示
        │
        ├── Enter key → push_screen(FactorDetailScreen(scores[idx]))
        │     ModalScreen 全屏展示因子明细 + LLM 解读
        │     Esc/点击背景关闭
        │
        ├── G key → 调用 report.generate_report + exporter.export_report
        │     Footer 提示 "报告已生成: report/xxx.md"
        │
        └── Q key → app.exit()
```

### 数据加载流程

1. `on_mount` 时表格显示 1 行占位文本："⏳ 正在加载数据..."
2. 后台 Worker 依次执行：`load_config` → `fetch_all` (逐个指数) → `calculate_index_score` → `interpret_direct` (有打分的才解读)
3. Worker 通过 `self.post_message(DataReady(scores, interpretations))` 将结果推送到 UI 线程
4. 表格收到 `DataReady` 消息后 `clear()` + 逐行 `add_row()`

## 文件结构

```
src/index_score/ui/
├── __init__.py                    (已有)
├── app.py                         — IndexScoreApp 主框架
└── widgets/
    ├── __init__.py                (已有)
    ├── score_table.py             — ScoreTable (DataTable wrapper)
    ├── factor_detail.py           — FactorDetailScreen (ModalScreen)
    └── action_bar.py              — ActionBar (Static)

main.py                            — CLI 入口
```

## 组件设计

### ScoreTable (score_table.py)

**类**：`ScoreTable(Widget)` — 封装 Textual DataTable

**列定义**：

| 列名 | 宽度 | 数据来源 |
|------|------|---------|
| 指数名称 | auto | `score.name` |
| 代码 | 10 | `score.code` |
| 模板 | 10 | `score.template` |
| 总分 | 8 | `score.total_score` |
| 估值水平 | 10 | `score.label` |

**颜色规则**（行级别着色）：
- `total_score <= 3` → 绿色（便宜）
- `3 < total_score <= 6` → 黄色（中性）
- `total_score > 6` → 红色（偏贵）
- `total_score == 0` → 灰色（数据不足）

**排序**：默认按总分升序（便宜的在前），与 report 的 `sort_by: "score"` 一致。

**方法**：
- `refresh_data(scores: list[IndexScore])` — 清空表格并重新填充
- `show_loading()` — 显示占位行 "⏳ 正在加载数据..."
- `show_error(msg: str)` — 显示错误行
- `get_selected_score() -> IndexScore | None` — 返回当前选中行对应的 IndexScore

**不展示因子分列**（PE/PB/股息率/价格位置各占一列）— 不同模板因子不同，列太多拥挤。因子详情通过 Enter 在 Modal 中查看。

### FactorDetailScreen (factor_detail.py)

**类**：`FactorDetailScreen(ModalScreen)` — 因子详情 + LLM 解读弹窗

**布局**：
```
┌──────────────────────────────────────────────────────┐
│  ✕ 关闭 (Esc)                                        │
│                                                      │
│  ## 中证红利 (000922) — 7.4 分 · 偏贵                │
│                                                      │
│  ### 估值概况                                         │
│  | 指标       | 当前值 | 5年分位 | 分数 | 权重 |      │
│  |------------|--------|---------|------|------|      │
│  | PE(TTM)    | 8.74   | 96.7%   | 9.0  | 30%  |    │
│  | PB         | 0.82   | 93.5%   | 9.0  | -    |    │
│  | 股息率     | 4.1%   | 1.7%    | 1.0  | 45%  |    │
│  | 价格位置   | -      | 83.7%   | 7.4  | 25%  |    │
│                                                      │
│  ### LLM 解读                                        │
│  好的，根据您提供的中证红利指数数据...                 │
│  （完整 LLM 文本，支持垂直滚动）                      │
│                                                      │
│  ─────────────────────────────────────────────        │
│  [Esc] 关闭                                          │
└──────────────────────────────────────────────────────┘
```

**要点**：
- 使用 `Static` widget 渲染 Markdown 表格 + LLM 文本
- 内容超出可视区域时支持垂直滚动（`VerticalScroll` 容器）
- LLM 解读为空时显示 "暂无 LLM 解读"
- 数据不足的指数（total_score == 0）不显示分数列，只显示 "数据不足"
- 估值概况表包含原始估值绝对值（从 `score.valuation` 读取 PE/PB/股息率）
- Esc 键关闭 Modal

### ActionBar (action_bar.py)

**类**：`ActionBar(Static)` — 底部快捷键提示栏

**显示内容**：`[R] 刷新  [Enter] 详情  [G] 生成报告  [Q] 退出`

### IndexScoreApp (app.py)

**类**：`IndexScoreApp(App)` — 主应用框架

**CSS 布局**：
```
Screen {
  layout: vertical;
}
Header {
  dock: top;
  height: 1;
}
ScoreTable {
  height: 1fr;
}
ActionBar {
  dock: bottom;
  height: 1;
}
```

**自定义消息**：
- `DataReady(Message)` — 携带 `scores: list[IndexScore]` + `interpretations: dict[str, str]`
- `DataError(Message)` — 携带 `error: str`
- `StatusUpdate(Message)` — 携带 `text: str`（Footer 状态提示）

**快捷键绑定**：
- `r` → `action_refresh()` — 启动后台 Worker
- `enter` → `action_detail()` — 弹出详情 Modal
- `g` → `action_generate_report()` — 生成报告
- `q` → `action_quit()` — 退出

**状态管理**：
- `self._scores: list[IndexScore]` — 当前打分结果
- `self._interpretations: dict[str, str]` — LLM 解读缓存
- `self._config: AppConfig` — 配置对象
- `self._worker: Worker | None` — 当前运行中的 Worker 引用
- `self._refreshing: bool` — 是否正在刷新

### main.py (CLI 入口)

```python
"""CLI 入口：启动 Textual 终端界面。"""
from index_score.ui.app import IndexScoreApp

def main() -> None:
    app = IndexScoreApp()
    app.run()

if __name__ == "__main__":
    main()
```

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| Config 加载失败 | 启动时直接 `app.exit(error_message)` |
| 部分指数数据拉取失败 | 表格正常显示成功的，失败的不显示。Worker 内部 catch 单个指数异常，log warning，continue |
| 全部指数失败 | 表格显示 "❌ 数据拉取失败"，Footer 显示错误信息 |
| LLM 初始化失败 | 不阻塞，所有详情页显示 "暂无 LLM 解读" |
| LLM 单个解读失败 | `interpret_direct` 已有 fallback 机制，自动降级为纯文本描述 |
| 理杏仁 Token 未配置 | 估值数据缺失，降级为仅价格位置因子（已有 fallback 逻辑） |

## 运行方式

```bash
# 方式 1：通过 pyproject.toml 入口
python main.py

# 方式 2：模块运行
python -m index_score.main
```

`pyproject.toml` 已配置：
```toml
[project.scripts]
index-score = "index_score.main:main"
```

需更新 `index_score.main` 模块指向 `main.py` 中的 `main()` 函数。

## 测试策略

- `tests/test_ui.py` — 核心逻辑测试（不启动真实 Textual App）
  - ScoreTable 颜色映射逻辑
  - FactorDetailScreen 估值表渲染
  - App 状态管理（scores / interpretations 缓存）
  - 报告生成调用参数
- 不测试 Textual 框架本身的渲染（由 Textual 自身保证）
