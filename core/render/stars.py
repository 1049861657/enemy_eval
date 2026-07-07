"""评级星级绘制。"""

from __future__ import annotations

import math

import skia

from core.render.layout import darken


def _build_star_path(cx: float, cy: float, radius: float) -> skia.Path:
    """构造五角星路径（外半径 radius，内半径 radius*0.4 的交替顶点）。"""
    path = skia.Path()
    outer_radius = radius
    inner_radius = radius * 0.4

    path.moveTo(cx, cy - outer_radius)

    for i in range(1, 11):
        angle = i * math.pi / 5
        r = inner_radius if i % 2 == 1 else outer_radius
        x = cx + r * math.sin(angle)
        y = cy - r * math.cos(angle)
        path.lineTo(x, y)

    path.close()
    return path


def draw_premium_star(
    canvas: skia.Canvas,
    cx: float,
    cy: float,
    radius: float,
    color: tuple[float, float, float],
) -> None:
    path = _build_star_path(cx, cy, radius)

    gradient_colors = [
        skia.Color4f(*color, 1.0),
        skia.Color4f(*darken(color, 0.8), 1.0),
    ]
    gradient = skia.GradientShader.MakeRadial(
        center=(cx, cy),
        radius=radius,
        colors=gradient_colors,
    )
    paint = skia.Paint(Shader=gradient)
    canvas.drawPath(path, paint)

    border_paint = skia.Paint(
        Color=skia.Color4f(*darken(color, 0.6), 0.8)
    )
    border_paint.setStyle(skia.Paint.kStroke_Style)
    border_paint.setStrokeWidth(0.5)
    canvas.drawPath(path, border_paint)


def draw_empty_star(canvas: skia.Canvas, cx: float, cy: float, radius: float) -> None:
    path = _build_star_path(cx, cy, radius)

    paint = skia.Paint(Color=skia.Color4f(0.7, 0.7, 0.7, 1))
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(1)
    canvas.drawPath(path, paint)
