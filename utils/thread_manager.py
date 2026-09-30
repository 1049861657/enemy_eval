"""
卡片生成线程管理器
"""
import array
import asyncio
from typing import Optional

import skia
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage, QPixmap

from models import EnemyData, RenderOptions

from . import prts_enemy_builder as builder
from . import prts_mediawiki_pipeline as pipeline
from .error_handler import RenderError
from .update_checker import fetch_latest


class CardGeneratorThread(QThread):
    """卡片生成线程，避免 UI 阻塞；结果携带序号以便丢弃过时渲染。"""

    cardGenerated = Signal(object, int)
    errorOccurred = Signal(str, int)

    def __init__(self, enemy_data: EnemyData, options: RenderOptions, revision: int) -> None:
        super().__init__()
        self.enemy_data = enemy_data
        self._options = options
        self._revision = revision

    def run(self):
        """在后台线程中生成卡片预览图。"""
        from core import EnemyCardGenerator

        snapshot = self.enemy_data.model_copy(deep=True)
        options = self._options.model_copy(deep=True)

        try:
            if self.isInterruptionRequested():
                return

            generator = EnemyCardGenerator()
            skia_image = generator.generate_card_image(snapshot, options)

            if self.isInterruptionRequested():
                return

            qpixmap = self._skia_to_qpixmap(skia_image)
            if self.isInterruptionRequested():
                return
            if qpixmap:
                self.cardGenerated.emit(qpixmap, self._revision)

        except Exception as e:
            if not self.isInterruptionRequested():
                self.errorOccurred.emit(str(e), self._revision)

    def _skia_to_qpixmap(self, skia_image) -> Optional[QPixmap]:
        try:
            width = skia_image.width()
            height = skia_image.height()

            image_info = skia.ImageInfo.MakeN32Premul(width, height)
            row_bytes = width * 4

            pixel_buffer = array.array("B", [0] * (width * height * 4))

            success = skia_image.readPixels(image_info, pixel_buffer, row_bytes, 0, 0)
            if not success:
                raise RenderError("无法读取图像像素数据")

            pixels = bytes(pixel_buffer)

            qimage = QImage(
                pixels, width, height, QImage.Format.Format_RGBA8888_Premultiplied
            )
            qimage = qimage.rgbSwapped()
            return QPixmap.fromImage(qimage)

        except Exception as e:
            raise RenderError(f"图像转换失败: {str(e)}") from e


class PrtsFetchThread(QThread):
    """PRTS 数据拉取线程：避免 fetch 的 HTTP 请求 + 头像下载/解码阻塞主线程。"""

    fetchFinished = Signal(object, object)  # (Optional[EnemyData], Optional[str] error_msg)

    def __init__(self, enemy_name: str):
        super().__init__()
        self.enemy_name = enemy_name

    def run(self):
        """在后台线程中拉取 PRTS 数据并预下载头像。"""
        try:
            asyncio.run(self._fetch())
        except Exception as e:
            if not self.isInterruptionRequested():
                self.fetchFinished.emit(None, f"获取PRTS数据时发生错误：{str(e)}")

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
        from core.render.avatar_prefetch import preload_network_avatar_image

        async with pipeline.build_async_client() as client:
            if self.isInterruptionRequested():
                return

            raw = await pipeline.fetch_enemy_from_prts_mediawiki(
                self.enemy_name, client=client
            )
            if self.isInterruptionRequested():
                return

            if "error" in raw:
                self.fetchFinished.emit(
                    None, pipeline.error_message_for_raw(raw, self.enemy_name)
                )
                return

            clean = builder.strip_debug_keys(raw)
            if clean.get("avatar_path"):
                await preload_network_avatar_image(client, clean["avatar_path"])

            if self.isInterruptionRequested():
                return

            enemy_data = builder.to_enemy_data(clean, self.enemy_name)
            if enemy_data:
                self.fetchFinished.emit(enemy_data, None)
            else:
                self.fetchFinished.emit(None, "PRTS数据格式不兼容，无法导入。")


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
