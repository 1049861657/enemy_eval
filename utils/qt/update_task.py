"""版本检查长任务：UpdateCheckThread。

输入：上次响应留下的 ETag（空串即无条件请求）。
产出：checkFinished(outcome, tag, url, etag, retry_at)；结果只回主线程，写偏好由主线程决定。
取消：单次请求，requestInterruption 后不发信号；绝不 terminate。
线程内禁止：新建或访问 QWidget、写偏好文件。
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ..app.update_check import fetch_latest


class UpdateCheckThread(QThread):
    """版本检查线程。只发一次 releases/latest，不写偏好。"""

    checkFinished = Signal(str, str, str, str, float)

    def __init__(self, etag: str) -> None:
        super().__init__()
        self._etag = etag

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        result = fetch_latest(self._etag)
        if self.isInterruptionRequested():
            return
        self.checkFinished.emit(
            result.outcome, result.tag, result.url, result.etag, result.retry_at
        )
