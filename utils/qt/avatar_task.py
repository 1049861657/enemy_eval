"""网络头像补取长任务：NetworkAvatarPrefetchThread。

输入：头像 URL（加载配置或手填 URL 得到的地址，非 PRTS 导入路径）。
产出：prefetchFinished(bool) —— True 表示该 URL 已进入全局图像缓存，渲染可以画出来。
取消：requestInterruption 后以 50ms 粒度轮询取消；绝不 terminate。
线程内禁止：新建或访问 QWidget、写偏好文件；渲染线程不下载，未命中即跳过不画。
core.render.avatar_prefetch 延迟导入（`_pull` 内）——缓存读写属渲染层职责。
"""

from __future__ import annotations

import asyncio

from PySide6.QtCore import QThread, Signal

from ..prts import pipeline as pipeline


class NetworkAvatarPrefetchThread(QThread):
    """网络头像补取线程：把非 PRTS 路径得到的 URL 取进图像缓存。

    渲染线程不下载网络图、未命中即不画头像；完成后由 GUI 重绘一次
    （`gui/main_window.py::_ensure_avatar_cached`）。
    """

    prefetchFinished = Signal(bool)  # True 表示头像已进入图像缓存

    def __init__(self, avatar_url: str):
        super().__init__()
        self.avatar_url = avatar_url

    def run(self):
        """在后台线程中下载并解码网络头像。"""
        try:
            asyncio.run(self._fetch())
        except Exception:
            if not self.isInterruptionRequested():
                self.prefetchFinished.emit(False)

    async def _fetch(self) -> None:
        task = asyncio.create_task(self._pull())
        try:
            while not task.done():
                if self.isInterruptionRequested():
                    task.cancel()
                    break
                await asyncio.sleep(0.05)
            await task
        except asyncio.CancelledError:
            return

    async def _pull(self) -> None:
        from core.render.avatar_prefetch import (
            is_avatar_cached,
            preload_network_avatar_image,
        )

        async with pipeline.build_async_client() as client:
            if self.isInterruptionRequested():
                return
            await preload_network_avatar_image(client, self.avatar_url)

        if self.isInterruptionRequested():
            return
        self.prefetchFinished.emit(is_avatar_cached(self.avatar_url))
