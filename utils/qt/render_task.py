"""`CardGeneratorThread`：预览渲染，输出 `cardGenerated(QPixmap, revision)` 或 `errorOccurred`。

输入深拷贝一次；取消后不发信号。`core` 延迟导入，保持 utils 不模块级依赖 core。
"""

from __future__ import annotations

import array
from typing import Optional

import skia
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage, QPixmap

from models import EnemyData, RenderOptions

from ..errors import RenderError


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
