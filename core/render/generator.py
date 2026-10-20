"""卡片生成器：`generate_card_image` / `save_card_image` 是对外入口，`_draw_card` 是唯一绘制入口。

画布来自 `canvas_pool`（超高卡片用非池化 Surface）；渲染串行驱动，实例状态不加锁；不读偏好。
"""

from __future__ import annotations

from typing import Optional

import skia

from models import EnemyData, RenderOptions
from utils.fs.filenames import safe_filename

from . import layout
from .canvas_pool import CanvasPool, get_canvas_pool
from .config import RenderConfig
from .font_cache import get_font
from .fonts import FontManager, get_font_manager
from .image_ops import ImageProcessor
from .sections import avatar, info, rating_grade, skills_talents
from .text_layout import get_text_layout
from .timing import PerformanceTimer


class EnemyCardGenerator:

    def __init__(
        self,
        canvas_pool: Optional[CanvasPool] = None,
        font_manager: Optional[FontManager] = None,
    ):
        self.config = RenderConfig()
        self.width = self.config.width
        self.height = self.config.height

        self._canvas_pool = canvas_pool or get_canvas_pool()
        self.image_processor = ImageProcessor()

        self.surface: Optional[skia.Surface] = None
        self.canvas: Optional[skia.Canvas] = None

        self.font_manager = font_manager or get_font_manager()

        self.grade_colors = {
            "S": (0.85, 0.2, 0.5, 1.0),
            "A": (0.2, 0.7, 0.9, 1.0),
            "B": (0.3, 0.8, 0.3, 1.0),
            "C": (0.9, 0.7, 0.2, 1.0),
            "D": (0.6, 0.6, 0.6, 1.0),
        }

        self._render_count = 0
        self._render_height: int = self.config.height
        self._canvas_from_pool: bool = True

    def _init_canvas(self, render_height: Optional[int] = None) -> None:
        h = int(render_height or self.config.height)
        self._render_height = h
        if h == self.config.height:
            self.surface, self.canvas = self._canvas_pool.acquire_canvas()
            self._canvas_from_pool = True
        else:
            self.surface, self.canvas = self._canvas_pool.acquire_variable_canvas(
                self.config.width, h
            )
            self._canvas_from_pool = False
        self._draw_background_gradient()

    def _draw_background_gradient(self) -> None:
        gradient_colors = [
            skia.Color4f(0.95, 0.95, 0.98, 1.0),
            skia.Color4f(0.92, 0.92, 0.95, 1.0),
        ]
        gradient = skia.GradientShader.MakeLinear(
            points=[(0, 0), (self.width, self._render_height)],
            colors=gradient_colors,
        )
        paint = skia.Paint(Shader=gradient)
        assert self.canvas is not None
        self.canvas.drawPaint(paint)

    def _cleanup_canvas(self) -> None:
        if not self.surface or not self.canvas:
            return
        if self._canvas_from_pool:
            self._canvas_pool.release_canvas(self.surface, self.canvas)
        self.surface = None
        self.canvas = None

    def _get_optimized_font(self, size: int) -> skia.Font:
        typeface = self.font_manager.chinese_font if self.font_manager.chinese_font else None
        return get_font(size, typeface)

    def _measure_render_height(self, enemy: EnemyData, options: RenderOptions) -> int:
        return layout.measure_render_height(
            enemy,
            self.config.height,
            self.font_manager,
            self._wrap_text,
            rating_radar=options.rating_radar,
        )

    def _wrap_text(self, text: str, max_width: int, font_size: int) -> list[str]:
        if not text:
            return [""]
        typeface = self.font_manager.chinese_font if self.font_manager.chinese_font else None
        layout_result = get_text_layout(text, max_width, font_size, typeface)
        return layout_result.lines

    def _draw_card(self, enemy: EnemyData, options: RenderOptions) -> skia.Image:
        self._render_count += 1
        with PerformanceTimer(f"绘制卡片#{self._render_count}"):
            try:
                self._init_canvas(self._measure_render_height(enemy, options))
                avatar.draw_avatar_section(self, enemy)
                info_section_bottom = info.draw_info_section(self, enemy)
                skills_section_bottom = skills_talents.draw_skills_talents_section(
                    self, enemy, int(info_section_bottom)
                )
                rating_grade.draw_rating_section(self, enemy, options)
                rating_grade.draw_grade_section(self, enemy, options, skills_section_bottom)
                assert self.surface is not None
                return self.surface.makeImageSnapshot()
            finally:
                self._cleanup_canvas()

    def generate_card(
        self,
        enemy: EnemyData,
        options: RenderOptions,
        output_path: Optional[str] = None,
    ) -> str:
        image = self._draw_card(enemy, options)
        if not output_path:
            output_path = f"{safe_filename(enemy.name)}.png"
        image.save(output_path, skia.kPNG)
        return output_path

    def generate_card_image(self, enemy: EnemyData, options: RenderOptions) -> skia.Image:
        return self._draw_card(enemy, options)
