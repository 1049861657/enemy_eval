"""
网络图片支持工具 - 最小侵入性实现
"""

import hashlib
import logging
from typing import Optional

import httpx

from models.media import is_url
from utils.prts.api_client import request_timeout

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
    """用已有 AsyncClient 流式下载图片；失败返回 None。可被 task.cancel 打断。"""
    if not is_url(url):
        return None

    try:
        async with client.stream(
            "GET", url, timeout=request_timeout(timeout)
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
    """为URL生成缓存键"""
    return f"url_{hashlib.md5(url.encode()).hexdigest()}"
