"""渲染协调器 - 管理卡片生成线程的生命周期与结果分发。

职责：
  - 持有 generator_thread、_pending_render、_preview_revision、last_generated_pixmap
  - 对外暴露 request()（触发渲染）和 save_current()（导出图片）
  - 通过信号回传结果；调用方（MainWindow）只做 UI 编排

MainWindow 不再直接接触 CardGeneratorThread。
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from utils import CardGeneratorThread, RenderError, categorize_error_message, error_handler
from models import EnemyData

logger = logging.getLogger(__name__)


class RenderCoordinator(QObject):
    """卡片渲染线程编排与结果分发。"""

    # 渲染完成：(result, revision)；result 为 QPixmap（预览）或文件路径字符串（导出）
    cardReady = Signal(object, int)
    # 渲染失败：(error_message,)
    renderFailed = Signal(str)
    # 忙碌状态变化：True = 开始渲染，False = 渲染结束（成功或失败）
    busyChanged = Signal(bool)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._generator_thread: Optional[CardGeneratorThread] = None
        self._pending_render: bool = False
        self._revision: int = 0
        self.last_generated_pixmap: Optional[QPixmap] = None
        self.last_generated_path: str = ""
        self._pending_data: Optional[EnemyData] = None

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def request(self, enemy_data: EnemyData) -> None:
        """请求渲染（任意时刻只允许一个线程运行）。

        若已有线程在跑，只发出中断请求并标记排队；线程结束后自动用此刻最新的
        enemy_data 快照发起下一次渲染——天然合并排队期间的多次编辑。
        """
        if self._generator_thread is not None and self._generator_thread.isRunning():
            self._generator_thread.requestInterruption()
            self._pending_render = True
            self._pending_data = enemy_data
            return
        self._start(enemy_data)

    def save_current(self, file_path: str) -> bool:
        """把最近一次渲染结果保存到 file_path。返回是否成功。"""
        if self.last_generated_pixmap is None:
            return False
        with error_handler("导出图片"):
            ok = self.last_generated_pixmap.save(file_path)
            if not ok:
                raise RenderError("图片保存失败")
        return True

    def cleanup(self) -> None:
        """窗口关闭前等待线程结束（最多 3 秒）。"""
        t = self._generator_thread
        if t is not None and t.isRunning():
            t.requestInterruption()
            if not t.wait(3000):
                logger.warning("渲染线程未能在预期时间内停止")
                t.terminate()
                t.wait(1000)
        self.last_generated_pixmap = None

    # ──────────────────────────────────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────────────────────────────────

    def _start(self, enemy_data: EnemyData) -> None:
        self._revision += 1
        rev = self._revision
        self._pending_data = None

        thread = CardGeneratorThread(enemy_data, revision=rev, save_to_file=False)
        thread.cardGenerated.connect(self._on_card_generated)
        thread.errorOccurred.connect(self._on_generation_error)
        thread.finished.connect(lambda thr=thread: self._on_thread_finished(thr))

        self._generator_thread = thread
        self.busyChanged.emit(True)
        thread.start()

    def _on_thread_finished(self, thread: CardGeneratorThread) -> None:
        thread.deleteLater()
        if self._generator_thread is thread:
            self._generator_thread = None
        if self._pending_render:
            self._pending_render = False
            pending = self._pending_data
            self._pending_data = None
            if pending is not None:
                self._start(pending)
            # busyChanged(False) 将在下一次 _on_thread_finished 发出
        else:
            self.busyChanged.emit(False)

    def _on_card_generated(self, result: object, revision: int) -> None:
        if revision != self._revision:
            return
        if isinstance(result, QPixmap):
            self.last_generated_pixmap = result
            self.last_generated_path = ""
        else:
            self.last_generated_path = str(result)
            self.last_generated_pixmap = None
        self.cardReady.emit(result, revision)

    def _on_generation_error(self, error_message: str, revision: int) -> None:
        if revision != self._revision:
            return
        logger.error(f"卡片生成失败: {error_message}")
        self.renderFailed.emit(error_message)
