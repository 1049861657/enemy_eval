"""`UpdateCheckThread`：releases/latest 条件请求，结果（含 ETag、退避时间）只回主线程。

写偏好由主线程决定；取消后不发信号。
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
