"""左侧头像与名称。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import skia

from models import EnemyData

from core.render.layout import center_text_x

if TYPE_CHECKING:
    from core.render.generator import EnemyCardGenerator


def draw_avatar_section(gen: "EnemyCardGenerator", enemy: EnemyData) -> None:
    canvas = gen.canvas
    avatar_rect = skia.Rect(45, 45, 405, 405)

    shadow_paint = skia.Paint(Color=skia.Color4f(0, 0, 0, 0.1))
    shadow_rect = skia.Rect(57, 57, 417, 417)
    canvas.drawRoundRect(shadow_rect, 24, 24, shadow_paint)

    bg_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 0.95))
    canvas.drawRoundRect(avatar_rect, 18, 18, bg_paint)

    border_paint = skia.Paint(
        Color=skia.Color4f(*gen.grade_colors.get(enemy.grade, (0.6, 0.6, 0.6, 0.8)))
    )
    border_paint.setStyle(skia.Paint.kStroke_Style)
    border_paint.setStrokeWidth(6)
    canvas.drawRoundRect(avatar_rect, 18, 18, border_paint)

    if enemy.avatar_path:
        skia_img = gen.image_processor.load_avatar_optimized(
            enemy.avatar_path, target_size=(330, 330)
        )

        if skia_img:
            img_rect = skia.Rect(60, 60, 390, 390)
            canvas.drawImageRect(skia_img, img_rect)
        else:
            print(f"头像加载失败: {enemy.avatar_path}")

    font = gen._get_optimized_font(48)
    font.setEmbolden(True)
    paint = skia.Paint(Color=skia.Color4f(0.1, 0.1, 0.1, 1), AntiAlias=True)

    text_width = font.measureText(enemy.name)
    text_x = center_text_x(avatar_rect.left(), avatar_rect.width(), text_width)
    canvas.drawString(enemy.name, text_x, 465, font, paint)
