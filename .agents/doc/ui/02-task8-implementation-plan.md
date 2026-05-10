# Task 8: Textual 终端界面 Implementation Plan

> **For agentic workers:** Execute task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive terminal UI using Textual that displays index scores in a sortable table, supports async data refresh, detail drill-down via modal, and report generation.

**Architecture:** Textual App with ScoreTable widget (DataTable), FactorDetailScreen (ModalScreen), and ActionBar. Data is loaded asynchronously via Textual Workers. Scores and LLM interpretations are cached in App state.

**Tech Stack:** Textual >= 0.80, Rich >= 13.0 (already in pyproject.toml dependencies)

---

### Task 1: ScoreTable Widget

**Files:**
- Create: `src/index_score/ui/widgets/score_table.py`
- Modify: `src/index_score/ui/widgets/__init__.py`
- Create: `tests/test_ui.py`

- [ ] **Step 1: Write tests for ScoreTable**

```python
# tests/test_ui.py
"""UI 组件核心逻辑测试。"""

from __future__ import annotations

from index_score.config.models import FactorScore, IndexScore
from index_score.ui.widgets.score_table import score_color


def _score(
    *,
    code: str = "000922",
    name: str = "中证红利",
    template: str = "dividend",
    total_score: float = 3.2,
    label: str = "便宜",
) -> IndexScore:
    return IndexScore(
        code=code,
        name=name,
        template=template,
        date="2026-05-10",
        total_score=total_score,
        label=label,
        factors=[],
    )


def test_score_color_cheap():
    assert score_color(_score(total_score=1.0)) == "green"
    assert score_color(_score(total_score=3.0)) == "green"


def test_score_color_neutral():
    assert score_color(_score(total_score=3.1)) == "yellow"
    assert score_color(_score(total_score=5.0)) == "yellow"
    assert score_color(_score(total_score=6.0)) == "yellow"


def test_score_color_expensive():
    assert score_color(_score(total_score=6.1)) == "red"
    assert score_color(_score(total_score=9.0)) == "red"


def test_score_color_no_data():
    assert score_color(_score(total_score=0.0)) == "grey"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'index_score.ui.widgets.score_table'`

- [ ] **Step 3: Create ScoreTable widget**

```python
# src/index_score/ui/widgets/score_table.py
"""打分表格组件。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import DataTable, Static

if TYPE_CHECKING:
    from index_score.config.models import IndexScore

COLUMNS = [
    ("指数名称", "auto"),
    ("代码", 10),
    ("模板", 10),
    ("总分", 8),
    ("估值水平", 10),
]

SCORE_COLOR_MAP: dict[str, str] = {
    "green": "$success",
    "yellow": "$warning",
    "red": "$error",
    "grey": "$text-muted",
}


def score_color(score: IndexScore) -> str:
    s = score.total_score
    if s <= 0:
        return "grey"
    if s <= 3:
        return "green"
    if s <= 6:
        return "yellow"
    return "red"


class ScoreTable(Static):
    """封装 DataTable，提供指数打分表格展示。"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._sorted_scores: list[IndexScore] = []

    def compose(self):
        table = DataTable(cursor_type="row")
        table.focus()
        yield table

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for label, width in COLUMNS:
            if width == "auto":
                table.add_column(label, width=None)
            else:
                table.add_column(label, width=width)

    def show_loading(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        self._sorted_scores = []
        table.add_row("⏳ 正在加载数据...", "", "", "", "")

    def show_error(self, msg: str) -> None:
        table = self.query_one(DataTable)
        table.clear()
        self._sorted_scores = []
        table.add_row(f"❌ {msg}", "", "", "", "")

    def refresh_data(self, scores: list[IndexScore]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        if not scores:
            self.show_error("无可用打分数据")
            return
        self._sorted_scores = sorted(scores, key=lambda s: s.total_score)
        for s in self._sorted_scores:
            color_key = score_color(s)
            color_css = SCORE_COLOR_MAP.get(color_key, "$text")
            score_str = f"{s.total_score:.1f}" if s.total_score > 0 else "0.0"
            table.add_row(
                s.name,
                s.code,
                s.template,
                score_str,
                s.label,
                style=color_css,
            )

    def get_selected_score(self) -> IndexScore | None:
        table = self.query_one(DataTable)
        if table.cursor_row is None or not self._sorted_scores:
            return None
        row = table.cursor_row
        if 0 <= row < len(self._sorted_scores):
            return self._sorted_scores[row]
        return None
```

- [ ] **Step 4: Update widgets __init__.py**

```python
# src/index_score/ui/widgets/__init__.py
"""自定义 Textual 组件。"""

from index_score.ui.widgets.score_table import ScoreTable

__all__ = ["ScoreTable"]
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_ui.py -v`
Expected: 4 tests PASS

- [ ] **Step 6: Run ruff**

Run: `python -m ruff check src/index_score/ui/ tests/test_ui.py`
Expected: All checks passed

---

### Task 2: FactorDetailScreen Modal

**Files:**
- Create: `src/index_score/ui/widgets/factor_detail.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write tests for FactorDetailScreen content building**

Append to `tests/test_ui.py`:

```python
from index_score.config.models import IndexValuation
from index_score.ui.widgets.factor_detail import build_detail_content


def _score_with_factors() -> IndexScore:
    return IndexScore(
        code="000922",
        name="中证红利",
        template="dividend",
        date="2026-05-10",
        total_score=7.4,
        label="偏贵",
        factors=[
            FactorScore(
                field="dividend_yield_percentile_5y",
                label="便宜",
                percentile=1.7,
                score=1.0,
                weight=0.45,
                original_weight=0.45,
            ),
            FactorScore(
                field="pe_percentile_5y",
                label="极贵",
                percentile=96.7,
                score=9.0,
                weight=0.30,
                original_weight=0.30,
            ),
            FactorScore(
                field="price_position_percentile_3y",
                label="偏贵",
                percentile=83.7,
                score=7.4,
                weight=0.25,
                original_weight=0.25,
            ),
        ],
        price_position_percentile=83.7,
        valuation=IndexValuation(
            code="000922",
            date="2026-05-10",
            pe_ttm=8.74,
            pe_percentile_5y=96.7,
            pb_lf=0.82,
            pb_percentile_5y=93.5,
            dividend_yield=0.041,
            dividend_yield_percentile_5y=1.7,
        ),
    )


def test_build_detail_content_title():
    content = build_detail_content(_score_with_factors(), "test interp")
    assert "中证红利 (000922)" in content
    assert "7.4" in content
    assert "偏贵" in content


def test_build_detail_content_factors():
    content = build_detail_content(_score_with_factors(), "test interp")
    assert "股息率" in content
    assert "PE" in content
    assert "83.7%" in content


def test_build_detail_content_llm():
    interp = "这是一段LLM解读文本"
    content = build_detail_content(_score_with_factors(), interp)
    assert interp in content


def test_build_detail_content_no_llm():
    content = build_detail_content(_score_with_factors(), "")
    assert "暂无 LLM 解读" in content


def test_build_detail_content_no_data():
    s = IndexScore(
        code="999999",
        name="测试指数",
        template="value",
        date="2026-05-10",
        total_score=0.0,
        label="数据不足",
        factors=[],
    )
    content = build_detail_content(s, "")
    assert "数据不足" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui.py::test_build_detail_content_title -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create FactorDetailScreen**

```python
# src/index_score/ui/widgets/factor_detail.py
"""因子详情 ModalScreen。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

if TYPE_CHECKING:
    from index_score.config.models import IndexScore

FIELD_LABELS: dict[str, str] = {
    "pe_percentile_5y": "PE(TTM)",
    "pb_percentile_5y": "PB",
    "dividend_yield_percentile_5y": "股息率",
    "price_position_percentile_3y": "价格位置",
}

VALUATION_FIELDS: list[tuple[str, str, bool]] = [
    ("pe_ttm", "PE(TTM)", False),
    ("pb_lf", "PB", False),
    ("dividend_yield", "股息率", True),
]

_PERCENTILE_MAP: dict[str, str] = {
    "pe_ttm": "pe_percentile_5y",
    "pb_lf": "pb_percentile_5y",
    "dividend_yield": "dividend_yield_percentile_5y",
}


def _fmt_val(v: float | None, pct: bool = False) -> str:
    if v is None:
        return "-"
    if pct:
        return f"{v:.2%}"
    return f"{v:.2f}"


def build_detail_content(score: IndexScore, interpretation: str) -> str:
    """构建详情 Modal 的纯文本内容。"""
    lines: list[str] = []

    title = (
        f"## {score.name} ({score.code})"
        f" — {score.total_score:.1f} 分 · {score.label}"
    )
    lines.append(title)
    lines.append("")

    lines.append("### 估值概况")
    lines.append("")

    if score.total_score <= 0:
        lines.append("数据不足，无法计算估值指标。")
    else:
        lines.append(
            f"{'指标':<12} {'当前值':>8} {'5年分位':>8} {'分数':>6} {'权重':>6}"
        )
        lines.append("-" * 46)

        if score.valuation:
            v = score.valuation
            for attr, label, is_pct in VALUATION_FIELDS:
                raw = getattr(v, attr, None)
                val_str = _fmt_val(raw, is_pct)

                pct_field = _PERCENTILE_MAP.get(attr, "")
                pct_val = getattr(v, pct_field, None) if pct_field else None
                pct_str = f"{pct_val:.1f}%" if pct_val is not None else "-"

                factor_score = "-"
                factor_weight = "-"
                for f in score.factors:
                    if f.field == pct_field:
                        factor_score = f"{f.score:.1f}"
                        factor_weight = f"{f.weight:.0%}"
                        break

                lines.append(
                    f"{label:<12} {val_str:>8} {pct_str:>8}"
                    f" {factor_score:>6} {factor_weight:>6}"
                )

        if score.price_position_percentile is not None:
            pp_score = "-"
            pp_weight = "-"
            for f in score.factors:
                if f.field == "price_position_percentile_3y":
                    pp_score = f"{f.score:.1f}"
                    pp_weight = f"{f.weight:.0%}"
                    break
            lines.append(
                f"{'价格位置':<12} {'-':>8}"
                f" {score.price_position_percentile:.1f}%"
                f" {pp_score:>6} {pp_weight:>6}"
            )

    lines.append("")
    lines.append("### LLM 解读")
    lines.append("")

    if interpretation.strip():
        lines.append(interpretation)
    else:
        lines.append("暂无 LLM 解读。")

    return "\n".join(lines)


class FactorDetailScreen(ModalScreen[None]):
    """因子详情 + LLM 解读的 ModalScreen。"""

    DEFAULT_CLASSES = "factor-detail-screen"
    BINDINGS = [Binding("escape", "dismiss", "关闭")]

    def __init__(self, score: IndexScore, interpretation: str) -> None:
        super().__init__()
        self._score = score
        self._interpretation = interpretation

    def compose(self) -> ComposeResult:
        content = build_detail_content(self._score, self._interpretation)
        with VerticalScroll():
            yield Static(content, markup=False)
        yield Static("[Esc] 关闭", classes="footer-hint")

    def action_dismiss(self) -> None:
        self.dismiss()
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_ui.py -v`
Expected: 9 tests PASS

- [ ] **Step 5: Run ruff**

Run: `python -m ruff check src/index_score/ui/widgets/factor_detail.py tests/test_ui.py`
Expected: All checks passed

---

### Task 3: ActionBar Widget

**Files:**
- Create: `src/index_score/ui/widgets/action_bar.py`
- Modify: `src/index_score/ui/widgets/__init__.py`

- [ ] **Step 1: Create ActionBar widget**

```python
# src/index_score/ui/widgets/action_bar.py
"""底部快捷键提示栏。"""

from __future__ import annotations

from textual.widgets import Static


class ActionBar(Static):
    """底部快捷键操作栏。"""

    DEFAULT_CONTENT = "[R] 刷新  [Enter] 详情  [G] 生成报告  [Q] 退出"

    def on_mount(self) -> None:
        self.update(self.DEFAULT_CONTENT)
```

- [ ] **Step 2: Update widgets __init__.py**

```python
# src/index_score/ui/widgets/__init__.py
"""自定义 Textual 组件。"""

from index_score.ui.widgets.action_bar import ActionBar
from index_score.ui.widgets.factor_detail import FactorDetailScreen
from index_score.ui.widgets.score_table import ScoreTable

__all__ = ["ActionBar", "FactorDetailScreen", "ScoreTable"]
```

- [ ] **Step 3: Run ruff**

Run: `python -m ruff check src/index_score/ui/`
Expected: All checks passed

---

### Task 4: IndexScoreApp 主框架

**Files:**
- Create: `src/index_score/ui/app.py`
- Modify: `src/index_score/ui/__init__.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write tests for App message types**

Append to `tests/test_ui.py`:

```python
from index_score.ui.app import DataError, DataReady, StatusUpdate


def test_data_ready_message():
    msg = DataReady(scores=[], interpretations={})
    assert msg.scores == []
    assert msg.interpretations == {}


def test_data_error_message():
    msg = DataError(error="test error")
    assert msg.error == "test error"


def test_status_update_message():
    msg = StatusUpdate(text="loading...")
    assert msg.text == "loading..."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui.py::test_data_ready_message -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create IndexScoreApp**

```python
# src/index_score/ui/app.py
"""Textual App 主框架。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Footer, Header, Static

from index_score.ui.widgets.action_bar import ActionBar
from index_score.ui.widgets.factor_detail import FactorDetailScreen
from index_score.ui.widgets.score_table import ScoreTable

if TYPE_CHECKING:
    from index_score.config.models import AppConfig, IndexScore

logger = logging.getLogger(__name__)


class DataReady(Message):
    """数据加载完成消息。"""

    def __init__(
        self,
        scores: list[IndexScore],
        interpretations: dict[str, str],
    ) -> None:
        super().__init__()
        self.scores = scores
        self.interpretations = interpretations


class DataError(Message):
    """数据加载失败消息。"""

    def __init__(self, error: str) -> None:
        super().__init__()
        self.error = error


class StatusUpdate(Message):
    """状态栏更新消息。"""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


APP_CSS = """\
Screen {
    layout: vertical;
}
#score-table {
    height: 1fr;
}
#action-bar {
    dock: bottom;
    height: auto;
    padding: 0 1;
}
#status-bar {
    dock: bottom;
    height: auto;
    padding: 0 1;
}
.factor-detail-screen VerticalScroll {
    height: 1fr;
}
.factor-detail-screen Static {
    width: 1fr;
}
.factor-detail-screen .footer-hint {
    dock: bottom;
    height: auto;
    padding: 0 1;
}
"""


class IndexScoreApp(App[None]):
    """大盘指数量化打分终端界面。"""

    CSS = APP_CSS
    TITLE = "大盘指数量化打分"
    BINDINGS = [
        Binding("r", "refresh", "刷新", show=False),
        Binding("enter", "detail", "详情", show=False),
        Binding("g", "generate_report", "报告", show=False),
        Binding("q", "quit", "退出", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._scores: list[IndexScore] = []
        self._interpretations: dict[str, str] = {}
        self._config: AppConfig | None = None
        self._refreshing: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="status-bar")
        yield ScoreTable(id="score-table")
        yield ActionBar(id="action-bar")

    def on_mount(self) -> None:
        self.query_one(ScoreTable).show_loading()
        self._fetch_data()

    @work(exclusive=True, thread=True)
    def _fetch_data(self) -> None:
        """后台 Worker：拉取数据、计算打分、调用 LLM。"""
        try:
            from dotenv import load_dotenv

            load_dotenv(
                Path(__file__).resolve().parent.parent.parent.parent / ".env"
            )
        except ImportError:
            pass

        try:
            from index_score.config.loader import load_config
            from index_score.data.fallback import fetch_all
            from index_score.data.lixinger import LixingerClient
            from index_score.llm.agent import build_llm, interpret_direct
            from index_score.scoring.calculator import (
                calculate_index_score,
                calculate_price_position,
            )
        except ImportError as exc:
            self.post_message(DataError(error=f"模块导入失败: {exc}"))
            return

        try:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            config = load_config(project_root / "config.yaml")
        except Exception as exc:
            self.post_message(DataError(error=f"配置加载失败: {exc}"))
            return

        self._config = config
        self.post_message(StatusUpdate(text="⏳ 正在拉取数据..."))

        lixinger_client = None
        if config.lixinger and config.lixinger.token:
            lixinger_client = LixingerClient(config.lixinger)

        price_years = config.scoring.price_position_years
        scores: list[IndexScore] = []

        for idx_info in config.indexes:
            try:
                result = fetch_all(
                    idx_info,
                    lixinger_client=lixinger_client,
                    price_years=price_years,
                )
                pp = calculate_price_position(result.quotes, price_years)
                score = calculate_index_score(
                    idx_info,
                    result.valuation,
                    pp,
                    config.scoring,
                    config.score_ranges,
                )
                scores.append(score)
            except Exception as exc:
                logger.warning("指数 %s 数据拉取失败: %s", idx_info.code, exc)

        if not scores:
            self.post_message(DataError(error="所有指数数据拉取失败"))
            return

        self.post_message(StatusUpdate(text="⏳ 正在生成 LLM 解读..."))

        llm = None
        interpretations: dict[str, str] = {}
        try:
            llm = build_llm(config.llm)
        except Exception as exc:
            logger.warning("LLM 初始化失败: %s", exc)

        if llm:
            for s in scores:
                if s.total_score <= 0:
                    continue
                try:
                    interp = interpret_direct(llm, s)
                    interpretations[s.code] = interp
                except Exception as exc:
                    logger.warning("指数 %s LLM 解读失败: %s", s.code, exc)

        self.post_message(
            DataReady(scores=scores, interpretations=interpretations)
        )

    @on(DataReady)
    def _on_data_ready(self, event: DataReady) -> None:
        self._scores = event.scores
        self._interpretations = event.interpretations
        table = self.query_one(ScoreTable)
        table.refresh_data(self._scores)
        self._refreshing = False
        self.query_one("#status-bar", Static).update("✅ 数据已更新")

    @on(DataError)
    def _on_data_error(self, event: DataError) -> None:
        table = self.query_one(ScoreTable)
        table.show_error(event.error)
        self._refreshing = False
        self.query_one("#status-bar", Static).update(f"❌ {event.error}")

    @on(StatusUpdate)
    def _on_status_update(self, event: StatusUpdate) -> None:
        self.query_one("#status-bar", Static).update(event.text)

    def action_refresh(self) -> None:
        if self._refreshing:
            return
        self._refreshing = True
        self.query_one(ScoreTable).show_loading()
        self._fetch_data()

    def action_detail(self) -> None:
        if not self._scores:
            return
        table = self.query_one(ScoreTable)
        target = table.get_selected_score()
        if target is None:
            return
        interp = self._interpretations.get(target.code, "")
        self.push_screen(FactorDetailScreen(target, interp))

    def action_generate_report(self) -> None:
        if not self._scores:
            self.query_one("#status-bar", Static).update(
                "❌ 无可用打分数据"
            )
            return

        try:
            from index_score.report.exporter import export_report
            from index_score.report.generator import generate_report
        except ImportError as exc:
            self.query_one("#status-bar", Static).update(
                f"❌ 报告模块导入失败: {exc}"
            )
            return

        sort_by = "score"
        if self._config and self._config.report:
            sort_by = self._config.report.sort_by

        content = generate_report(
            self._scores, self._interpretations, sort_by=sort_by
        )
        path = export_report(content)
        self.query_one("#status-bar", Static).update(
            f"✅ 报告已生成: {path}"
        )

    def action_quit(self) -> None:
        self.exit()
```

- [ ] **Step 4: Update ui __init__.py**

```python
# src/index_score/ui/__init__.py
"""Textual 终端 UI。"""

from index_score.ui.app import IndexScoreApp

__all__ = ["IndexScoreApp"]
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_ui.py -v`
Expected: 12 tests PASS

- [ ] **Step 6: Run ruff**

Run: `python -m ruff check src/index_score/ui/ tests/test_ui.py`
Expected: All checks passed

---

### Task 5: CLI 入口 (main.py)

**Files:**
- Create: `src/index_score/main.py`
- Create: `main.py` (根目录快捷入口)

- [ ] **Step 1: Create src/index_score/main.py**

```python
# src/index_score/main.py
"""CLI 入口：启动 Textual 终端界面。"""

from __future__ import annotations

from index_score.ui.app import IndexScoreApp


def main() -> None:
    app = IndexScoreApp()
    app.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create 根目录 main.py**

```python
# main.py
"""快捷入口：python main.py"""

from index_score.main import main

main()
```

- [ ] **Step 3: Run ruff**

Run: `python -m ruff check src/index_score/main.py main.py`
Expected: All checks passed

- [ ] **Step 4: Verify pyproject.toml entry point**

`pyproject.toml` 已配置 `index-score = "index_score.main:main"`，无需修改。

---

### Task 6: 额外测试 + 全量验证

**Files:**
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Add valuation-specific tests**

Append to `tests/test_ui.py`:

```python
def test_build_detail_content_with_valuation():
    score = _score_with_factors()
    content = build_detail_content(score, "some interpretation")
    assert "8.74" in content
    assert "0.82" in content
    assert "4.10%" in content


def test_build_detail_content_no_valuation():
    s = IndexScore(
        code="000922",
        name="中证红利",
        template="dividend",
        date="2026-05-10",
        total_score=7.4,
        label="偏贵",
        factors=[
            FactorScore(
                field="price_position_percentile_3y",
                label="偏贵",
                percentile=83.7,
                score=7.4,
                weight=1.0,
                original_weight=1.0,
            ),
        ],
        price_position_percentile=83.7,
    )
    content = build_detail_content(s, "test")
    assert "83.7%" in content


def test_get_selected_score_empty():
    from index_score.ui.widgets.score_table import ScoreTable

    table = ScoreTable()
    assert table.get_selected_score() is None
```

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest tests/ -q`
Expected: 162+ tests PASS (existing + new UI tests)

- [ ] **Step 3: Run ruff on all source**

Run: `python -m ruff check src/ tests/`
Expected: All checks passed

---

### Task 7: 手动验收

- [ ] **Step 1: 启动应用**

Run: `python main.py`
Expected: Textual 界面启动，显示 Header + "⏳ 正在加载数据..." + ActionBar

- [ ] **Step 2: 验证数据加载**

等待 1-2 分钟，表格应显示指数打分结果，按总分升序排列

- [ ] **Step 3: 验证颜色**

- 便宜的指数（≤3分）行显示绿色
- 中性指数（3-6分）行显示黄色
- 偏贵指数（>6分）行显示红色
- 数据不足（0分）行显示灰色

- [ ] **Step 4: 验证 Enter 详情**

选中一行按 Enter，应弹出 Modal 显示因子明细表 + LLM 解读。按 Esc 关闭。

- [ ] **Step 5: 验证 G 生成报告**

按 G，Footer 应显示 "✅ 报告已生成: report/指数打分报告_YYYYMMDD.md"

- [ ] **Step 6: 验证 R 刷新**

按 R，表格应显示 "⏳ 正在加载数据..."，然后异步刷新

- [ ] **Step 7: 验证 Q 退出**

按 Q，应用退出
