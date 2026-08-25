"""敌人评价卡片生成器：画布生命周期与分区编排。"""

from __future__ import annotations

from typing import Optional

import skia

from models import EnemyData
from utils.rating_schema_store import get_rating_names, is_rating_radar

from core.fonts import FontManager, get_font_manager
from core.optimization import (
    ImageProcessor,
    PerformanceTimer,
    RenderConfig,
    RenderResourceManager,
    get_resource_manager,
)

from . import layout
from .sections import avatar, info, rating_grade, skills_talents


class EnemyCardGenerator:
    """高性能敌人评价卡片生成器（Canvas 池、渐变背景、分区模块化绘制）。"""

    def __init__(
        self,
        resource_manager: Optional[RenderResourceManager] = None,
        font_manager: Optional[FontManager] = None,
    ):
        self.config = RenderConfig()
        self.width = self.config.width
        self.height = self.config.height

        self.resource_manager = resource_manager or get_resource_manager()
        self.image_processor = ImageProcessor(self.resource_manager)

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
            self.surface, self.canvas = self.resource_manager.acquire_canvas()
            self._canvas_from_pool = True
        else:
            self.surface = skia.Surface(self.config.width, h)
            self.canvas = self.surface.getCanvas()
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
            self.resource_manager.release_canvas(self.surface, self.canvas)
        self.surface = None
        self.canvas = None

    def _get_optimized_font(self, size: int) -> skia.Font:
        typeface = self.font_manager.chinese_font if self.font_manager.chinese_font else None
        return self.resource_manager.get_font(size, typeface)

    def _measure_render_height(self, enemy: EnemyData) -> int:
        return layout.measure_render_height(
            enemy,
            self.config.height,
            self.font_manager,
            self._wrap_text,
            rating_dimension_count=len(get_rating_names()),
            rating_radar=is_rating_radar(),
        )

    def _wrap_text(self, text: str, max_width: int, font_size: int) -> list[str]:
        if not text:
            return [""]
        typeface = self.font_manager.chinese_font if self.font_manager.chinese_font else None
        layout_result = self.resource_manager.get_text_layout(
            text, max_width, font_size, typeface
        )
        return layout_result.lines

    def generate_card(self, enemy: EnemyData, output_path: Optional[str] = None) -> str:
        self._render_count += 1

        with PerformanceTimer(f"卡片生成#{self._render_count}"):
            try:
                self._init_canvas(self._measure_render_height(enemy))

                with PerformanceTimer("头像区域渲染"):
                    avatar.draw_avatar_section(self, enemy)

                with PerformanceTimer("信息区域渲染"):
                    info_section_bottom = info.draw_info_section(self, enemy)

                with PerformanceTimer("技能区域渲染"):
                    skills_section_bottom = skills_talents.draw_skills_talents_section(
                        self, enemy, int(info_section_bottom)
                    )

                with PerformanceTimer("评价区渲染"):
                    rating_grade.draw_rating_section(self, enemy, int(skills_section_bottom))

                with PerformanceTimer("等级区域渲染"):
                    rating_grade.draw_grade_section(self, enemy, skills_section_bottom)

                if not output_path:
                    output_path = f"output_{enemy.name}_{enemy.grade}.png"

                with PerformanceTimer("图片保存"):
                    assert self.surface is not None
                    image = self.surface.makeImageSnapshot()
                    image.save(output_path, skia.kPNG)

                return output_path

            finally:
                self._cleanup_canvas()

    def generate_card_image(self, enemy: EnemyData) -> skia.Image:
        self._render_count += 1

        with PerformanceTimer(f"GUI预览渲染#{self._render_count}"):
            try:
                self._init_canvas(self._measure_render_height(enemy))

                avatar.draw_avatar_section(self, enemy)
                info_section_bottom = info.draw_info_section(self, enemy)
                skills_section_bottom = skills_talents.draw_skills_talents_section(
                    self, enemy, int(info_section_bottom)
                )
                rating_grade.draw_rating_section(self, enemy, int(skills_section_bottom))
                rating_grade.draw_grade_section(self, enemy, skills_section_bottom)

                assert self.surface is not None
                return self.surface.makeImageSnapshot()

            finally:
                self._cleanup_canvas()
