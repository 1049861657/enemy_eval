"""共享 pytest fixtures。

GUI 测试需要在导入/实例化任何 Qt 组件之前设置 `QT_QPA_PLATFORM=offscreen`，
并且整个测试会话只能存在一个 `QApplication` 实例，否则 PySide6 会报错或崩溃。
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="session")
def qapp():
    """会话级别的无头 QApplication，供所有 GUI 测试复用。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
