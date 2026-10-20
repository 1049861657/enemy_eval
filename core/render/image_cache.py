"""全局图像缓存与它的锁：本模块是唯一持有者。

读写一律经 `cache_get` / `cache_put` / `cache_has` / `cache_clear`（锁在访问器内），不得直接操作缓存对象。
"""

from __future__ import annotations

import threading
from typing import Optional

import skia
from cachetools import LRUCache

from .config import RenderConfig

_GLOBAL_IMAGE_CACHE: LRUCache = LRUCache(maxsize=RenderConfig.image_cache_size)
_GLOBAL_IMAGE_CACHE_LOCK = threading.Lock()


def cache_get(key: str) -> Optional[skia.Image]:
    """取缓存项；未命中返回 None。"""
    with _GLOBAL_IMAGE_CACHE_LOCK:
        return _GLOBAL_IMAGE_CACHE.get(key)


def cache_put(key: str, image: skia.Image) -> None:
    """写入缓存项；超出 maxsize 时淘汰最久未用项。"""
    with _GLOBAL_IMAGE_CACHE_LOCK:
        _GLOBAL_IMAGE_CACHE[key] = image


def cache_has(key: str) -> bool:
    """该键是否已有缓存项。"""
    with _GLOBAL_IMAGE_CACHE_LOCK:
        return _GLOBAL_IMAGE_CACHE.get(key) is not None


def cache_clear() -> None:
    """清空缓存；应用退出前经 `core/render/canvas_pool.py::clear_caches` 调用一次。"""
    with _GLOBAL_IMAGE_CACHE_LOCK:
        _GLOBAL_IMAGE_CACHE.clear()
