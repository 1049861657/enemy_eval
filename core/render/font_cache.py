"""字体实例缓存：按 (字号, typeface) 缓存「未修改模板」。

typeface 的加载由 `core/render/fonts.py::FontManager` 负责（进程内单例）；
本模块只做字号维度的复用。key = (字号, id(typeface))：字号为固定枚举，
故不设容量上限。
"""

from __future__ import annotations

import skia

_font_cache: dict[int, skia.Font] = {}


def get_font(size: int, typeface: skia.Typeface | None = None) -> skia.Font:
    """获取指定 (size, typeface) 的字体。

    返回值经 `makeWithSize()` 克隆而非直接复用缓存对象：调用方（如
    `avatar.py::draw_avatar_section` 经 `EnemyCardGenerator._get_optimized_font`）
    会对返回值原地 `setEmbolden(True)`，若直接返回缓存实例会污染同 key 的后续
    取用者（与 `core/render/fonts.py::FontManager.get_font` 的同类问题一致）。
    """
    cache_key = hash((size, id(typeface) if typeface else None))

    template = _font_cache.get(cache_key)
    if template is None:
        template = skia.Font(typeface, size)
        _font_cache[cache_key] = template
    return template.makeWithSize(size)


def clear_font_cache() -> None:
    """清空字体缓存；应用退出前经 `core/render/canvas_pool.py::clear_caches` 调用一次。"""
    _font_cache.clear()
