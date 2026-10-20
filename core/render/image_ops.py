"""图像加载与缩放：Skia 直读 + Mitchell 立方重采样。

只读 `core/render/image_cache.py` 的全局缓存、从不发起网络：网络头像由
`core/render/avatar_prefetch.py` 预取后写入同一缓存，未命中即跳过不画。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import skia
import structlog

from models.media import is_url
from utils.net.image_fetch import get_url_cache_key

from .image_cache import cache_get, cache_put

logger = structlog.get_logger(__name__)

_image_cache_hits: int = 0


class ImageProcessor:
    """图像加载与缩放：Skia 直读 + 全局缓存。"""

    @staticmethod
    def load_image_direct(path: str) -> Optional[skia.Image]:
        """按路径直读为 Skia 图像；文件不存在或解码失败返回 None。"""
        if not Path(path).exists():
            return None

        try:
            return skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(str(path)))
        except Exception as e:
            logger.warning("Skia直接加载失败，尝试兼容模式", error=str(e))
            return None

    # noinspection PyUnreachableCode
    def load_avatar_optimized(
        self, path: str, target_size: Tuple[int, int] = (330, 330)
    ) -> Optional[skia.Image]:
        """头像加载：本地文件按 mtime 缓存，网络 URL 只读缓存；缩放至 target_size。"""
        global _image_cache_hits
        if not path:
            return None

        if is_url(path):
            # 网络 URL：只读缓存，未命中即返回 None，不在渲染线程下载
            cache_key = f"{get_url_cache_key(path)}_{target_size}"

            cached = cache_get(cache_key)
            if cached is not None:
                _image_cache_hits += 1
                return cached

            # 网络头像由预取线程写入缓存（core/render/avatar_prefetch.py）
            logger.warning("网络图片未预缓存，跳过加载以避免渲染阻塞", path=path)
            return None
        else:
            # 本地文件：mtime 参与缓存键
            if not Path(path).exists():
                return None

            cache_key = f"{path}_{target_size}_{Path(path).stat().st_mtime}"

            cached = cache_get(cache_key)
            if cached is not None:
                _image_cache_hits += 1
                return cached

            original_image = self.load_image_direct(path)
            if not original_image:
                return None

        try:
            if (original_image.width(), original_image.height()) != target_size:
                target_w, target_h = target_size

                scaled_surface = skia.Surface(target_w, target_h)
                scaled_canvas = scaled_surface.getCanvas()

                # Mitchell 立方重采样
                sampling = skia.SamplingOptions(skia.CubicResampler.Mitchell())

                paint = skia.Paint()
                paint.setAntiAlias(True)

                src_rect = skia.Rect(0, 0, original_image.width(), original_image.height())
                dst_rect = skia.Rect(0, 0, target_w, target_h)

                scaled_canvas.drawImageRect(original_image, src_rect, dst_rect, sampling, paint)
                scaled_image = scaled_surface.makeImageSnapshot()
            else:
                scaled_image = original_image

            cache_put(cache_key, scaled_image)
            return scaled_image

        except Exception as e:
            logger.warning("优化图像加载失败", error=str(e))
            return None
