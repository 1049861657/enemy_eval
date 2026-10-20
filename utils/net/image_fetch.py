"""网络图片下载：流式取字节，并按 URL 生成缓存键。

边界：本模块只下载，不写全局图像缓存——缓存读写见 `core/render/avatar_prefetch.py` 与
`core/render/image_cache.py`；渲染侧只读缓存、未命中即跳过，从不下载。
失败一律返回 None（调用方按"没有这张图"处理），可被 `task.cancel()` 打断。
"""

import hashlib
import logging
from typing import Optional

import httpx

from models.media import is_url

from .transport import CONNECT_TIMEOUT, build_timeout

logger = logging.getLogger(__name__)

_CHUNK = 8192
DEFAULT_IMAGE_TIMEOUT = 10.0
DEFAULT_IMAGE_MAX_SIZE = 10 * 1024 * 1024


def _headers_reject_body(response: httpx.Response, max_size: int) -> bool:
    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        return True
    content_length = response.headers.get("content-length")
    return bool(content_length) and int(content_length) > max_size


async def download_image_data(
    client: httpx.AsyncClient,
    url: str,
    timeout: float = DEFAULT_IMAGE_TIMEOUT,
    max_size: int = DEFAULT_IMAGE_MAX_SIZE,
) -> Optional[bytes]:
    """用已有 AsyncClient 流式下载图片；失败返回 None。可被 task.cancel 打断。

    超时：read/write 取 timeout，connect/pool 取 CONNECT_TIMEOUT。
    """
    if not is_url(url):
        return None

    try:
        async with client.stream(
            "GET", url, timeout=build_timeout(connect=CONNECT_TIMEOUT, read=timeout)
        ) as response:
            response.raise_for_status()
            if _headers_reject_body(response, max_size):
                return None
            chunks = bytearray()
            async for chunk in response.aiter_bytes(_CHUNK):
                chunks.extend(chunk)
                if len(chunks) > max_size:
                    return None
            return bytes(chunks)
    except (httpx.HTTPError, OSError, ValueError) as e:
        logger.debug("下载网络图片失败 %s: %s", url, e)
        return None


def get_url_cache_key(url: str) -> str:
    """URL → 全局图像缓存键（`url_<md5>`）。只做键映射，不访问网络与缓存。"""
    return f"url_{hashlib.md5(url.encode()).hexdigest()}"
