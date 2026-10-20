"""预览图交付：把渲染线程交到主线程的 QPixmap 提供给 QML Image。

provider id 与查询参数是冻结契约：`image://enemy-card/current?revision=`（见
`gui/qml/pages/PreviewViewport.qml`）——`revision` 变化才会重新取图。
"""

from __future__ import annotations

from threading import Lock

from PySide6.QtGui import QImage, QPixmap
from PySide6.QtQuick import QQuickImageProvider


class CardImageProvider(QQuickImageProvider):
    """将渲染线程交付到主线程的预览图提供给 QML Image。"""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._image = QImage()
        self._lock = Lock()

    def set_pixmap(self, pixmap: QPixmap) -> None:
        """主线程收到新预览图后写入；取图线程不会读到半张图。"""
        with self._lock:
            self._image = pixmap.toImage()

    def requestImage(self, image_id: str, size, requested_size) -> QImage:  # noqa: N802
        """QML 取图：返回副本，并按请求尺寸缩放（源图缺失时返回空图）。"""
        del image_id
        with self._lock:
            image = self._image.copy()
        if not image.isNull() and requested_size.width() > 0 and requested_size.height() > 0:
            image = image.scaled(requested_size)
        if size is not None:
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image
