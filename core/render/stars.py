"""评级星级绘制。"""

from __future__ import annotations

import math

import skia


def draw_premium_star(
    canvas: skia.Canvas,
    cx: float,
    cy: float,
    radius: float,
    color: tuple[float, float, float],
) -> None:
    path = skia.Path()
    outer_radius = radius
    inner_radius = radius * 0.4

    path.moveTo(cx, cy - outer_radius)

    for i in range(1, 11):
        angle = i * math.pi / 5
        if i % 2 == 1:
            r = inner_radius
        else:
            r = outer_radius

        x = cx + r * math.sin(angle)
        y = cy - r * math.cos(angle)
        path.lineTo(x, y)

    path.close()

    gradient_colors = [
        skia.Color4f(*color, 1.0),
        skia.Color4f(color[0] * 0.8, color[1] * 0.8, color[2] * 0.8, 1.0),
    ]
    gradient = skia.GradientShader.MakeRadial(
        center=(cx, cy),
        radius=outer_radius,
        colors=gradient_colors,
    )
    paint = skia.Paint(Shader=gradient)
    canvas.drawPath(path, paint)

    border_paint = skia.Paint(
        Color=skia.Color4f(color[0] * 0.6, color[1] * 0.6, color[2] * 0.6, 0.8)
    )
    border_paint.setStyle(skia.Paint.kStroke_Style)
    border_paint.setStrokeWidth(0.5)
    canvas.drawPath(path, border_paint)


def draw_empty_star(canvas: skia.Canvas, cx: float, cy: float, radius: float) -> None:
    path = skia.Path()
    outer_radius = radius
    inner_radius = radius * 0.4

    path.moveTo(cx, cy - outer_radius)

    for i in range(1, 11):
        angle = i * math.pi / 5
        if i % 2 == 1:
            r = inner_radius
        else:
            r = outer_radius

        x = cx + r * math.sin(angle)
        y = cy - r * math.cos(angle)
        path.lineTo(x, y)

    path.close()

    paint = skia.Paint(Color=skia.Color4f(0.7, 0.7, 0.7, 1))
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(1)
    canvas.drawPath(path, paint)
