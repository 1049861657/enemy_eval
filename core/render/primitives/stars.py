"""五角星图元：实心填充 + 可选柔光，供评价记分板使用。"""

from __future__ import annotations

import math

import skia

_INNER_RATIO = 0.47


def build_star_path(cx: float, cy: float, radius: float) -> skia.Path:
    """外半径 radius、内半径 radius*0.47 的正五角星路径。"""
    path = skia.Path()
    inner = radius * _INNER_RATIO
    path.moveTo(cx, cy - radius)
    for i in range(1, 10):
        angle = i * math.pi / 5
        r = inner if i % 2 else radius
        path.lineTo(cx + r * math.sin(angle), cy - r * math.cos(angle))
    path.close()
    return path


def draw_star(
    canvas: skia.Canvas,
    cx: float,
    cy: float,
    radius: float,
    color: tuple[float, float, float],
    *,
    glow: float = 0.0,
) -> None:
    """绘制实心五角星；glow>0 时在星形外围叠一层同色高斯柔光。"""
    path = build_star_path(cx, cy, radius)
    if glow > 0.0:
        halo = skia.Paint(Color=skia.Color4f(*color, 0.42 * glow), AntiAlias=True)
        halo.setMaskFilter(
            skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, radius * 0.42)
        )
        canvas.drawPath(path, halo)
    canvas.drawPath(path, skia.Paint(Color=skia.Color4f(*color, 1.0), AntiAlias=True))
