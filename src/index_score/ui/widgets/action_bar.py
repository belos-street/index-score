"""底部快捷键提示栏。"""

from __future__ import annotations

from textual.widgets import Static


class ActionBar(Static):
    """底部快捷键操作栏。"""

    DEFAULT_CONTENT = "[R] 刷新  [Enter] 详情  [G] 生成报告  [Q] 退出"

    def on_mount(self) -> None:
        self.update(self.DEFAULT_CONTENT)
