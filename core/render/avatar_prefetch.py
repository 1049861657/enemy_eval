"""网络头像预取 → 全局图像缓存；渲染侧只查缓存、从不下载，未命中即跳过。

写入一律经 `image_cache` 的访问器（锁在访问器内）；调用点是 PRTS 拉取线程与头像补取线程。
"""

from __future__ import annotations

import logging

import httpx
import skia

from models.media import is_url
from utils.net.image_fetch import download_image_data, get_url_cache_key

from .image_cache import cache_has, cache_put

logger = logging.getLogger(__name__)

_AVATAR_TARGET_SIZE = (330, 330)


def avatar_cache_key(avatar_path: str) -> str:
    """网络头像在全局图像缓存中的键：URL 键 + 目标尺寸。

    与 `core/render/image_ops.py::load_avatar_optimized` 的取图口径必须同键，
    否则预取写进去的图渲染侧读不到。
    """
    return f"{get_url_cache_key(avatar_path)}_{_AVATAR_TARGET_SIZE}"


def is_avatar_cached(avatar_path: str) -> bool:
    """网络头像是否已在全局图像缓存中；已缓存则无需重新下载与重绘。"""
    if not avatar_path or not is_url(avatar_path):
        return False
    return cache_has(avatar_cache_key(avatar_path))


async def preload_network_avatar_image(
    client: httpx.AsyncClient, avatar_path: str
) -> None:
    """用已有客户端预下载网络头像到全局图像缓存，避免渲染线程拿不到图。"""
    if not avatar_path:
        return
    try:
        if not is_url(avatar_path):
            return
        image_data = await download_image_data(client, avatar_path)
        if not image_data:
            return

        cache_key = avatar_cache_key(avatar_path)
        original_image = skia.Image.MakeFromEncoded(image_data)
        if not original_image:
            return
        target_w, target_h = _AVATAR_TARGET_SIZE
        if (original_image.width(), original_image.height()) != (target_w, target_h):
            scaled_surface = skia.Surface(target_w, target_h)
            scaled_canvas = scaled_surface.getCanvas()
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
        logger.info("成功预缓存网络头像: %s", avatar_path)
    except Exception as e:
        logger.warning("预加载头像失败: %s", e)
