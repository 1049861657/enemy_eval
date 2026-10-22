"""`NetworkAvatarPrefetchThread`：把 URL 拉进全局图像缓存，完成发 `prefetchFinished(bool)`。

只服务「加载配置 / 手填 URL」路径；取消 50ms 轮询。`core` 延迟导入。
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

        async with pipeline.build_async_client(proxy_target=self.avatar_url) as client:
            if self.isInterruptionRequested():
                return
            await preload_network_avatar_image(client, self.avatar_url)

        if self.isInterruptionRequested():
            return
        self.prefetchFinished.emit(is_avatar_cached(self.avatar_url))
