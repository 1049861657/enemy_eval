"""渲染协调器：`CardGeneratorThread` 的生命周期与结果分发。

`busyChanged` 只挂在 `finished` 上——成功、异常、静默中断三条路径里它唯一必发。
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from models import EnemyData, RenderOptions
from utils.qt.render_task import CardGeneratorThread

logger = logging.getLogger(__name__)


class RenderCoordinator(QObject):

    # 渲染完成：(pixmap, revision)
    cardReady = Signal(object, int)
    # 渲染失败：(error_message,)
    renderFailed = Signal(str)
    # 忙碌状态变化：True = 开始渲染，False = 渲染结束；只由线程生命周期驱动，见模块文档
    busyChanged = Signal(bool)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._generator_thread: Optional[CardGeneratorThread] = None
        self._pending_render: bool = False
        self._pending_data: Optional[EnemyData] = None
        self._pending_options: Optional[RenderOptions] = None
        self._revision: int = 0
        self._busy: bool = False
        self.last_generated_pixmap: Optional[QPixmap] = None


    def request(self, enemy_data: EnemyData, options: RenderOptions) -> None:
        """请求渲染（任意时刻只允许一个线程运行）。

        若已有线程在跑，只发出中断请求并标记排队；线程结束后自动用此刻最新的
        enemy_data / options 快照发起下一次渲染——天然合并排队期间的多次编辑。
        """
        if self._generator_thread is not None and self._generator_thread.isRunning():
            self._generator_thread.requestInterruption()
            self._pending_render = True
            self._pending_data = enemy_data
            self._pending_options = options
            return
        self._start(enemy_data, options)

    def save_current(self, file_path: str) -> Optional[str]:
        """把最近一次渲染结果保存到 file_path。

        返回 None 表示成功；否则返回可直接展示给用户的错误描述。
        不会抛出异常——调用方无需 try/except。
        """
        if self.last_generated_pixmap is None:
            return "尚无可导出的卡片，请先生成预览。"
        try:
            ok = self.last_generated_pixmap.save(file_path)
        except Exception as e:
            logger.error(f"图片保存异常: {e}", exc_info=True)
            return f"图片保存异常：{e}"
        if not ok:
            return "图片保存失败，请检查路径和磁盘权限。"
        return None

    def cleanup(self) -> None:
        """窗口关闭前请求中断并等待线程结束（最多 3 秒）。超时不 terminate。"""
        t = self._generator_thread
        if t is not None and t.isRunning():
            t.requestInterruption()
            if not t.wait(3000):
                logger.error("渲染线程未能在 3 秒内停止，放弃等待且不 terminate")
        self.last_generated_pixmap = None


    def _set_busy(self, busy: bool) -> None:
        """带去重的忙碌状态设置；避免同一状态重复触发下游 UI 更新。"""
        if self._busy == busy:
            return
        self._busy = busy
        self.busyChanged.emit(busy)

    def _start(self, enemy_data: EnemyData, options: RenderOptions) -> None:
        self._revision += 1
        rev = self._revision
        self._pending_data = None
        self._pending_options = None

        thread = CardGeneratorThread(enemy_data, options, revision=rev)
        thread.cardGenerated.connect(self._on_card_generated)
        thread.errorOccurred.connect(self._on_generation_error)
        thread.finished.connect(lambda thr=thread: self._on_thread_finished(thr))

        self._generator_thread = thread
        self._set_busy(True)
        thread.start()

    def _on_thread_finished(self, thread: CardGeneratorThread) -> None:
        """线程终结的唯一收口：无论成功/失败/静默中断，都会走到这里。"""
        thread.deleteLater()
        if self._generator_thread is thread:
            self._generator_thread = None
        if self._pending_render:
            self._pending_render = False
            pending = self._pending_data
            pending_options = self._pending_options
            self._pending_data = None
            self._pending_options = None
            if pending is not None and pending_options is not None:
                self._start(pending, pending_options)
                return
        self._set_busy(False)

    def _on_card_generated(self, result: object, revision: int) -> None:
        if revision != self._revision:
            return
        if isinstance(result, QPixmap):
            self.last_generated_pixmap = result
            self.cardReady.emit(result, revision)

    def _on_generation_error(self, error_message: str, revision: int) -> None:
        if revision != self._revision:
            return
        logger.error(f"卡片生成失败: {error_message}")
        self.renderFailed.emit(error_message)
