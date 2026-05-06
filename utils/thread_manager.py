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

    def __init__(
        self,
        enemy_data,
        revision: int,
        save_to_file: bool = False,
        output_path: Optional[str] = None,
    ):
        super().__init__()
        self.enemy_data = enemy_data
        self._revision = revision
        self.save_to_file = save_to_file
        self.output_path = output_path

    def run(self):
        """在后台线程中生成卡片"""
        from core import EnemyCardGenerator

        snapshot = self.enemy_data.model_copy(deep=True)

        try:
            if self.isInterruptionRequested():
                return

            generator = EnemyCardGenerator()

            if self.save_to_file:
                output_path = generator.generate_card(snapshot, self.output_path)
                if not self.isInterruptionRequested():
                    self.cardGenerated.emit(output_path, self._revision)
            else:
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
