"""左侧评级卡与底部等级+简评。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import skia

from models import EnemyData

from core.render import layout
from core.render.stars import draw_empty_star, draw_premium_star

if TYPE_CHECKING:
    from core.render.generator import EnemyCardGenerator


def draw_rating_cards(
    gen: "EnemyCardGenerator", enemy: EnemyData, _skills_bottom_y: int
) -> None:
    ratings = [
        ("对策度", enemy.hostility_rating, (0.85, 0.2, 0.3)),
        ("创新度", enemy.innovation_rating, (0.2, 0.6, 0.9)),
        ("威胁度", enemy.threat_rating, (0.9, 0.5, 0.1)),
    ]

    start_x = 60
    start_y = 560
    card_width = 360
    card_height = 105
    spacing = 126

    for i, (name, rating, color) in enumerate(ratings):
        x = start_x
        y = start_y + i * spacing

        card_rect = skia.Rect(x, y, x + card_width, y + card_height)
        gradient_colors = [
            skia.Color4f(*color, 0.85),
            skia.Color4f(*layout.darken(color, 0.8), 0.85),
        ]
        gradient = skia.GradientShader.MakeLinear(
            points=[(x, y), (x, y + card_height)],
            colors=gradient_colors,
        )
        card_paint = skia.Paint(Shader=gradient)
        gen.canvas.drawRoundRect(card_rect, 18, 18, card_paint)

        border_paint = skia.Paint(Color=skia.Color4f(*color, 0.9))
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(4.5)
        gen.canvas.drawRoundRect(card_rect, 18, 18, border_paint)

        name_font = gen.font_manager.get_font(33)
        name_font.setEmbolden(True)
        name_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 1), AntiAlias=True)
        gen.canvas.drawString(name, x + 24, y + 66, name_font, name_paint)

        name_width = name_font.measureText(name)
        star_start_x = x + 45 + name_width
        star_size = 15
        for j in range(5):
            star_x = star_start_x + j * 33
            star_y = y + 54

            if j < rating:
                draw_premium_star(gen.canvas, star_x, star_y, star_size, (1.0, 0.9, 0.3))
            else:
                draw_empty_star(gen.canvas, star_x, star_y, star_size)


def draw_grade_section(gen: "EnemyCardGenerator", enemy: EnemyData, skills_bottom_y: float) -> None:
    block_h = layout.measure_grade_block_height(enemy, gen._wrap_text)
    spacing = 28
    margin = 15
    grade_start_y = max(
        skills_bottom_y + spacing,
        float(gen.config.height) - block_h - margin,
    )
    grade_bottom = grade_start_y + block_h

    grade_rect = skia.Rect(60, grade_start_y, 420, grade_bottom)
    grade_color = gen.grade_colors.get(enemy.grade, (0.6, 0.6, 0.6, 1.0))

    gradient_colors = [
        skia.Color4f(*grade_color),
        skia.Color4f(*layout.darken(grade_color[:3], 0.7), grade_color[3]),
    ]
    gradient = skia.GradientShader.MakeLinear(
        points=[(60, grade_start_y), (420, grade_bottom)],
        colors=gradient_colors,
    )
    grade_paint = skia.Paint(Shader=gradient)
    gen.canvas.drawRoundRect(grade_rect, 24, 24, grade_paint)

    border_paint = skia.Paint(Color=skia.Color4f(*grade_color))
    border_paint.setStyle(skia.Paint.kStroke_Style)
    border_paint.setStrokeWidth(4.5)
    gen.canvas.drawRoundRect(grade_rect, 24, 24, border_paint)

    grade_font = gen.font_manager.get_font(126)
    grade_font.setEmbolden(True)
    text_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 1), AntiAlias=True)

    shadow_paint = skia.Paint(Color=skia.Color4f(0, 0, 0, 0.3), AntiAlias=True)
    grade_width = grade_font.measureText(enemy.grade)
    grade_x = layout.center_text_x(grade_rect.left(), grade_rect.width(), grade_width)
    grade_baseline = grade_start_y + block_h / 2 + 30
    gen.canvas.drawString(enemy.grade, grade_x + 6, grade_baseline + 6, grade_font, shadow_paint)
    gen.canvas.drawString(enemy.grade, grade_x, grade_baseline, grade_font, text_paint)

    comment_rect = skia.Rect(480, grade_start_y, 1860, grade_bottom)

    comment_paint = skia.Paint(Color=skia.Color4f(0.96, 0.96, 0.96, 0.9))
    gen.canvas.drawRoundRect(comment_rect, 18, 18, comment_paint)

    comment_border = skia.Paint(Color=skia.Color4f(0.75, 0.75, 0.75, 0.8))
    comment_border.setStyle(skia.Paint.kStroke_Style)
    comment_border.setStrokeWidth(3)
    gen.canvas.drawRoundRect(comment_rect, 18, 18, comment_border)

    comment_font = gen.font_manager.get_font(layout.GRADE_COMMENT_FONT_SIZE)
    comment_text_paint = skia.Paint(Color=skia.Color4f(0.4, 0.4, 0.4, 1), AntiAlias=True)

    raw = (enemy.brief_comment or "").strip()
    lines = gen._wrap_text(raw, layout.COMMENT_WRAP_WIDTH, layout.GRADE_COMMENT_FONT_SIZE) if raw else [""]
    for i, line in enumerate(lines):
        y_pos = grade_start_y + layout.COMMENT_FIRST_BASELINE + i * layout.COMMENT_LINE_STEP
        if i == 0:
            line = f"简评：{line}"
        else:
            line = f"      {line}"
        gen.canvas.drawString(line, 510, y_pos, comment_font, comment_text_paint)
