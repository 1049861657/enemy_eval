"""
卡片生成线程管理器
"""
import array
from typing import Optional

import skia
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage, QPixmap

from .error_handler import RenderError


class CardGeneratorThread(QThread):
    """卡片生成线程，避免 UI 阻塞；结果携带序号以便丢弃过时渲染。"""

    cardGenerated = Signal(object, int)
    errorOccurred = Signal(str, int)

    def __init__(self, enemy_data, revision: int):
        super().__init__()
        self.enemy_data = enemy_data
        self._revision = revision

    def run(self):
        """在后台线程中生成卡片预览图。"""
        from core import EnemyCardGenerator

        snapshot = self.enemy_data.model_copy(deep=True)

        try:
            if self.isInterruptionRequested():
                return

            generator = EnemyCardGenerator()
            skia_image = generator.generate_card_image(snapshot)

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
    """PRTS 数据拉取线程：避免 fetch_enemy_data 的两次 HTTP 请求 + 头像下载/解码阻塞主线程。"""

    fetchFinished = Signal(object, object)  # (Optional[EnemyData], Optional[str] error_msg)

    def __init__(self, enemy_name: str):
        super().__init__()
        self.enemy_name = enemy_name

    def run(self):
        """在后台线程中拉取 PRTS 数据并预下载头像。"""
        from core.render.avatar_prefetch import preload_prts_avatar_image
        from utils.prts_enemy_builder import strip_debug_keys, to_enemy_data
        from utils.prts_mediawiki_pipeline import (
            error_message_for_raw,
            fetch_enemy_from_prts_mediawiki,
        )

        try:
            if self.isInterruptionRequested():
                return

            raw = fetch_enemy_from_prts_mediawiki(self.enemy_name)
            if self.isInterruptionRequested():
                return

            if "error" in raw:
                self.fetchFinished.emit(None, error_message_for_raw(raw, self.enemy_name))
                return

            clean = strip_debug_keys(raw)
            if clean.get("avatar_path"):
                preload_prts_avatar_image(clean["avatar_path"])

            if self.isInterruptionRequested():
                return

            enemy_data = to_enemy_data(clean, self.enemy_name)
            if enemy_data:
                self.fetchFinished.emit(enemy_data, None)
            else:
                self.fetchFinished.emit(None, "PRTS数据格式不兼容，无法导入。")
        except Exception as e:
            if not self.isInterruptionRequested():
                self.fetchFinished.emit(None, f"获取PRTS数据时发生错误：{str(e)}")
