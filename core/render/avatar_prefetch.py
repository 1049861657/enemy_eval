"""网络头像预下载 → 写入渲染层全局图像缓存。

不变量：渲染侧对 URL 只查缓存、从不下载（`core.optimization.load_avatar_optimized`
未命中即跳过），因此网络头像必须先落进缓存。调用点：`PrtsFetchThread`（拿到
EnemyData 之前）、`NetworkAvatarPrefetchThread`（加载配置 / 手填 URL 之后）。

`_GLOBAL_IMAGE_CACHE` 可被渲染线程与上述两个线程并发读写，统一用
core.optimization 的最小粒度锁。
"""

from __future__ import annotations

import logging

import httpx
import skia

from core.optimization import _GLOBAL_IMAGE_CACHE, _GLOBAL_IMAGE_CACHE_LOCK
from models.media import is_url
from utils.network_image import download_image_data, get_url_cache_key

logger = logging.getLogger(__name__)

_AVATAR_TARGET_SIZE = (330, 330)


def is_avatar_cached(avatar_path: str) -> bool:
    """网络头像是否已在全局图像缓存中；已缓存则无需重新下载与重绘。"""
    if not avatar_path or not is_url(avatar_path):
        return False
    cache_key = f"{get_url_cache_key(avatar_path)}_{_AVATAR_TARGET_SIZE}"
    with _GLOBAL_IMAGE_CACHE_LOCK:
        return _GLOBAL_IMAGE_CACHE.get(cache_key) is not None


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

        cache_key = f"{get_url_cache_key(avatar_path)}_{_AVATAR_TARGET_SIZE}"
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
        with _GLOBAL_IMAGE_CACHE_LOCK:
            _GLOBAL_IMAGE_CACHE[cache_key] = scaled_image
        logger.info("成功预缓存网络头像: %s", avatar_path)
    except Exception as e:
        logger.warning("预加载头像失败: %s", e)
