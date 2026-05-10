"""Textual App 主框架。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Header, Static

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
                logger.warning(
                    "指数 %s 数据拉取失败: %s", idx_info.code, exc
                )

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
                    logger.warning(
                        "指数 %s LLM 解读失败: %s", s.code, exc
                    )

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
        self.query_one("#status-bar", Static).update(
            f"❌ {event.error}"
        )

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
