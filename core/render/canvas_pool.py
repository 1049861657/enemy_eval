"""画布复用池：默认尺寸池 + 可变高度备用 Surface。

线程约束：渲染由 `gui/render_coordinator.py::RenderCoordinator` 串行驱动（任意时刻只运行一个
渲染线程），故池内状态不加锁；跨线程的只有 `core/render/image_cache.py` 的全局图像缓存。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import skia

from .config import RenderConfig
from .font_cache import clear_font_cache
from .image_cache import cache_clear
from .text_layout import clear_text_layout_cache


class CanvasPool:
    """Surface / Canvas 复用池。

    默认尺寸池按 `RenderConfig.canvas_pool_size` 预建；同尺寸的备用 Surface 复用同一张，
    尺寸变化时替换（只保留最近一次非默认尺寸）。池满后新建的临时 Surface 不入池。
    """

    def __init__(self, config: Optional[RenderConfig] = None):
        self.config = config or RenderConfig()

        # Canvas 复用池：避免重复创建 Surface
        self._canvas_pool: List[Tuple[skia.Surface, skia.Canvas]] = []
        self._canvas_in_use: set = set()

        # 性能统计
        self._stats = {'canvas_reuse_count': 0}

        # 可变高度备用 Surface：只保留最近一次非默认尺寸
        self._variable_surface: Optional[Tuple[int, int, skia.Surface]] = None

        # 初始化Canvas池
        self._init_canvas_pool()

    def _init_canvas_pool(self):
        """初始化Canvas复用池"""
        for _ in range(self.config.canvas_pool_size):
            surface = skia.Surface(self.config.width, self.config.height)
            canvas = surface.getCanvas()
            self._canvas_pool.append((surface, canvas))

    def acquire_canvas(self) -> Tuple[skia.Surface, skia.Canvas]:
        """获取复用的Canvas"""
        # 优先从池中获取未使用的Canvas
        for i, (surface, canvas) in enumerate(self._canvas_pool):
            if i not in self._canvas_in_use:
                self._canvas_in_use.add(i)
                self._stats['canvas_reuse_count'] += 1

                # 清空Canvas但保持配置
                canvas.clear(skia.Color4f(0, 0, 0, 0))
                return surface, canvas

        # 池已满，创建新的临时Canvas
        surface = skia.Surface(self.config.width, self.config.height)
        canvas = surface.getCanvas()
        return surface, canvas

    def acquire_variable_canvas(
        self, width: int, height: int
    ) -> Tuple[skia.Surface, skia.Canvas]:
        """按 (width, height) 复用一张备用 Surface；尺寸变化时替换。"""
        cached = self._variable_surface
        if cached is not None and cached[0] == width and cached[1] == height:
            surface = cached[2]
            canvas = surface.getCanvas()
            canvas.clear(skia.Color4f(0, 0, 0, 0))
            self._stats["canvas_reuse_count"] += 1
            return surface, canvas
        surface = skia.Surface(width, height)
        self._variable_surface = (width, height, surface)
        return surface, surface.getCanvas()

    def release_canvas(self, surface: skia.Surface, canvas: skia.Canvas):
        """释放Canvas回池"""
        for i, (pool_surface, pool_canvas) in enumerate(self._canvas_pool):
            if pool_surface == surface:
                self._canvas_in_use.discard(i)
                break

    def discard_variable_surface(self) -> None:
        """丢弃可变高度备用 Surface（退出前清理，见本模块 `clear_caches`）。"""
        self._variable_surface = None


# 全局单例：EnemyCardGenerator 每次实例化复用同一画布池（字体模板同理，见 font_cache）。
_global_canvas_pool: Optional[CanvasPool] = None


def get_canvas_pool() -> CanvasPool:
    """获取全局画布池单例"""
    global _global_canvas_pool
    if _global_canvas_pool is None:
        _global_canvas_pool = CanvasPool()
    return _global_canvas_pool


def clear_caches() -> None:
    """清空渲染期全部缓存：可变 Surface、字体缓存、文本布局缓存、全局图像缓存。

    应用退出前调用一次（`gui/main_window.py` 的 `closeEvent`）；单帧内不调用，
    否则每帧重建字体与布局会丢掉缓存收益。
    """
    get_canvas_pool().discard_variable_surface()
    clear_font_cache()
    clear_text_layout_cache()
    cache_clear()
