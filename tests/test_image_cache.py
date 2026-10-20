"""全局图像缓存的唯一持有者与锁（core/render/image_cache.py）。

预取侧写入的键必须与渲染侧查询的键一致，否则头像永远画不出来。
"""

from __future__ import annotations

import threading

import skia


class TestGlobalImageCacheLock:

    def test_global_image_cache_lock_exists(self):
        from core.render import image_cache

        assert isinstance(image_cache._GLOBAL_IMAGE_CACHE_LOCK, threading.Lock)

    def test_avatar_prefetch_shares_the_single_cache(self):
        from core.render import avatar_prefetch, image_cache

        url = "https://example.com/avatar.png"
        key = avatar_prefetch.avatar_cache_key(url)
        image_cache.cache_put(key, skia.Surface(1, 1).makeImageSnapshot())
        try:
            assert image_cache.cache_has(key) is True
            # 预取写入的键必须就是渲染侧查的键，否则头像永远画不出来
            assert avatar_prefetch.is_avatar_cached(url) is True
        finally:
            image_cache.cache_clear()
        assert avatar_prefetch.is_avatar_cached(url) is False

