"""PRTS 头像预下载 → 写入渲染层全局图像缓存。

头像下载 + Skia 解码/缩放属于渲染层职责，放在 core 而非 utils（utils 不应反向依赖
core）。调用方（GUI 层的 PrtsFetchThread，见 utils/thread_manager.py）在拿到
EnemyData 前预下载头像，减轻首次渲染阻塞。

`_GLOBAL_IMAGE_CACHE` 可能被渲染线程（CardGeneratorThread）与本模块的调用方
（PrtsFetchThread）并发读写，因此复用 core.optimization 里为该缓存配的最小粒度锁。
"""

from __future__ import annotations

import logging

import httpx
import skia

from core.optimization import _GLOBAL_IMAGE_CACHE, _GLOBAL_IMAGE_CACHE_LOCK
from utils.network_image import download_image_data, get_url_cache_key, is_url

logger = logging.getLogger(__name__)

_AVATAR_TARGET_SIZE = (330, 330)


async def preload_prts_avatar_image(
    client: httpx.AsyncClient, avatar_path: str
) -> None:
    """用已有客户端预下载网络头像到全局图像缓存，减轻首次渲染阻塞。"""
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
        logger.info("成功预缓存 PRTS 头像: %s", avatar_path)
    except Exception as e:
        logger.warning("预加载头像失败: %s", e)
