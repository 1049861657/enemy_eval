"""全局图像缓存与它的锁：本模块是唯一持有者。

渲染线程（`utils/qt/render_task.py::CardGeneratorThread`）与预取线程
（`PrtsFetchThread` / `NetworkAvatarPrefetchThread`，见 `core/render/avatar_prefetch.py`）
会并发读写，因此读写一律经 `cache_get` / `cache_put` / `cache_has` / `cache_clear`，
锁在访问器内部获取；调用方不得绕过访问器直接操作缓存对象。
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
