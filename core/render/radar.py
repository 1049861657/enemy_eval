"""评价维度雷达图（Skia Path；与星级卡互斥展示）。"""

from __future__ import annotations

import math

import skia

from core.fonts import FontManager
from core.render.layout import (
    RATING_RADAR_BOX,
    RATING_RADAR_START_X,
    RATING_SECTION_TOP,
    rating_color_at,
)

_SCORE_MAX = 5
_GRID_RINGS = 5
_LABEL_FONT_SIZE = 21
_LABEL_LINE_GAP = 2.0
_PILL_PAD_X = 10.0
_PILL_PAD_Y = 5.0
_LAYOUT_INSET = 10.0
_LABEL_GAP = 12.0
_START_ANGLE = -math.pi / 2.0
_PILL_RADIUS = 9.0


def _axis_angle(index: int, count: int) -> float:
    return _START_ANGLE + 2.0 * math.pi * index / count


def _polar(cx: float, cy: float, radius: float, angle: float) -> tuple[float, float]:
    return (cx + math.cos(angle) * radius, cy + math.sin(angle) * radius)


def _polygon_points(
    cx: float, cy: float, radius: float, count: int
) -> list[tuple[float, float]]:
    return [_polar(cx, cy, radius, _axis_angle(i, count)) for i in range(count)]


def _polygon_path(points: list[tuple[float, float]]) -> skia.Path:
    path = skia.Path()
    path.moveTo(points[0][0], points[0][1])
    for x, y in points[1:]:
        path.lineTo(x, y)
    path.close()
    return path


def _split_label(name: str) -> tuple[str, ...]:
    text = name.strip()
    if len(text) <= 4:
        return (text,)
    mid = (len(text) + 1) // 2
    return (text[:mid], text[mid:])


def _stroke_paint(
    color: tuple[float, float, float, float],
    width: float,
) -> skia.Paint:
    paint = skia.Paint(Color=skia.Color4f(*color), AntiAlias=True)
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(width)
    paint.setStrokeJoin(skia.Paint.kRound_Join)
    paint.setStrokeCap(skia.Paint.kRound_Cap)
    return paint


def _fill_paint(color: tuple[float, float, float, float]) -> skia.Paint:
    return skia.Paint(Color=skia.Color4f(*color), AntiAlias=True)


def _label_metrics(
    font: skia.Font, names: list[str]
) -> list[tuple[tuple[str, ...], float, float]]:
    line_h = _LABEL_FONT_SIZE + _LABEL_LINE_GAP
    out: list[tuple[tuple[str, ...], float, float]] = []
    for name in names:
        lines = _split_label(name)
        width = max(font.measureText(line) for line in lines)
        height = len(lines) * line_h - _LABEL_LINE_GAP
        out.append((lines, width, height))
    return out


def _pill_rect(
    cx: float,
    cy: float,
    radius: float,
    angle: float,
    text_w: float,
    text_h: float,
) -> skia.Rect:
    pill_w = text_w + _PILL_PAD_X * 2.0
    pill_h = text_h + _PILL_PAD_Y * 2.0
    lx, ly = _polar(cx, cy, radius + _LABEL_GAP, angle)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    if cos_a < -0.25:
        left = lx - pill_w
    elif cos_a > 0.25:
        left = lx
    else:
        left = lx - pill_w / 2.0
    if sin_a < -0.45:
        top = ly - pill_h
    elif sin_a > 0.45:
        top = ly
    else:
        top = ly - pill_h / 2.0
    return skia.Rect(left, top, left + pill_w, top + pill_h)


def _pills_inside(
    cx: float,
    cy: float,
    radius: float,
    metrics: list[tuple[tuple[str, ...], float, float]],
    bounds: skia.Rect,
) -> bool:
    n = len(metrics)
    for i, (_lines, text_w, text_h) in enumerate(metrics):
        pill = _pill_rect(cx, cy, radius, _axis_angle(i, n), text_w, text_h)
        if (
            pill.left() < bounds.left()
            or pill.top() < bounds.top()
            or pill.right() > bounds.right()
            or pill.bottom() > bounds.bottom()
        ):
            return False
    return True


def _fit_radius(
    cx: float,
    cy: float,
    metrics: list[tuple[tuple[str, ...], float, float]],
    bounds: skia.Rect,
) -> float:
    geometric = min(
        cx - bounds.left(),
        bounds.right() - cx,
        cy - bounds.top(),
        bounds.bottom() - cy,
    )
    hi = max(48.0, geometric - 6.0)
    lo = 36.0
    if _pills_inside(cx, cy, hi, metrics, bounds):
        return hi
    for _ in range(22):
        mid = (lo + hi) / 2.0
        if _pills_inside(cx, cy, mid, metrics, bounds):
            lo = mid
        else:
            hi = mid
    return lo


def _draw_grid(
    canvas: skia.Canvas,
    cx: float,
    cy: float,
    radius: float,
    count: int,
) -> None:
    if count >= 3:
        shell = _polygon_path(_polygon_points(cx, cy, radius, count))
        canvas.drawPath(shell, _fill_paint((0.55, 0.62, 0.78, 0.06)))
    for ring in range(1, _GRID_RINGS + 1):
        t = ring / _GRID_RINGS
        r = radius * t
        alpha = 0.18 + 0.42 * t
        width = 1.05 + 1.15 * t
        paint = _stroke_paint((0.52, 0.58, 0.68, alpha), width)
        if count >= 3:
            canvas.drawPath(_polygon_path(_polygon_points(cx, cy, r, count)), paint)
        else:
            canvas.drawCircle(cx, cy, r, paint)
    axis_paint = _stroke_paint((0.48, 0.54, 0.64, 0.42), 1.35)
    for i in range(count):
        x, y = _polar(cx, cy, radius, _axis_angle(i, count))
        canvas.drawLine(cx, cy, x, y, axis_paint)
    canvas.drawCircle(cx, cy, 7.0, _fill_paint((0.22, 0.48, 0.86, 0.12)))
    canvas.drawCircle(cx, cy, 7.0, _stroke_paint((0.45, 0.55, 0.72, 0.55), 1.6))
    canvas.drawCircle(cx, cy, 2.4, _fill_paint((0.22, 0.48, 0.86, 0.85)))


def _draw_labels(
    canvas: skia.Canvas,
    font: skia.Font,
    names: list[str],
    metrics: list[tuple[tuple[str, ...], float, float]],
    cx: float,
    cy: float,
    radius: float,
) -> None:
    line_step = _LABEL_FONT_SIZE + _LABEL_LINE_GAP
    n = len(names)
    for i, ((lines, text_w, text_h), name) in enumerate(zip(metrics, names)):
        del name
        angle = _axis_angle(i, n)
        pill = _pill_rect(cx, cy, radius, angle, text_w, text_h)
        color = rating_color_at(i)
        canvas.drawRoundRect(
            pill,
            _PILL_RADIUS,
            _PILL_RADIUS,
            _fill_paint((*color, 0.14)),
        )
        canvas.drawRoundRect(
            pill,
            _PILL_RADIUS,
            _PILL_RADIUS,
            _stroke_paint((*color, 0.42), 1.35),
        )
        text_paint = skia.Paint(Color=skia.Color4f(0.22, 0.24, 0.28, 1.0), AntiAlias=True)
        text_left = pill.left() + _PILL_PAD_X
        baseline = pill.top() + _PILL_PAD_Y + _LABEL_FONT_SIZE * 0.82
        for line in lines:
            canvas.drawString(line, text_left, baseline, font, text_paint)
            baseline += line_step


def _draw_data_polygon(
    canvas: skia.Canvas,
    points: list[tuple[float, float]],
    cx: float,
    cy: float,
    radius: float,
) -> None:
    if len(points) < 3:
        if len(points) == 2:
            canvas.drawLine(
                points[0][0],
                points[0][1],
                points[1][0],
                points[1][1],
                _stroke_paint((0.12, 0.42, 0.86, 0.95), 3.2),
            )
        return
    path = _polygon_path(points)
    glow = _stroke_paint((0.18, 0.48, 0.95, 0.18), 9.0)
    canvas.drawPath(path, glow)
    fill = skia.Paint(AntiAlias=True)
    fill.setShader(
        skia.GradientShader.MakeRadial(
            center=(cx, cy),
            radius=radius,
            colors=[
                skia.Color4f(0.28, 0.58, 0.98, 0.42),
                skia.Color4f(0.14, 0.36, 0.82, 0.14),
            ],
        )
    )
    canvas.drawPath(path, fill)
    canvas.drawPath(path, _stroke_paint((0.95, 0.97, 1.0, 0.55), 4.4))
    canvas.drawPath(path, _stroke_paint((0.10, 0.40, 0.88, 0.96), 2.6))


def _draw_vertices(canvas: skia.Canvas, points: list[tuple[float, float]]) -> None:
    for i, (x, y) in enumerate(points):
        color = rating_color_at(i)
        canvas.drawCircle(x, y, 6.2, _fill_paint((*color, 1.0)))
        canvas.drawCircle(x, y, 6.2, _stroke_paint((1.0, 1.0, 1.0, 0.95), 1.8))
        canvas.drawCircle(x, y, 2.1, _fill_paint((1.0, 1.0, 1.0, 0.88)))


def draw_rating_radar(
    canvas: skia.Canvas,
    font_manager: FontManager,
    names: list[str],
    scores: list[int],
) -> None:
    """在左侧评价区绘制雷达图；names 与 scores 等长且非空。"""
    box = float(RATING_RADAR_BOX)
    x0 = float(RATING_RADAR_START_X)
    y0 = float(RATING_SECTION_TOP)
    area = skia.Rect(x0, y0, x0 + box, y0 + box)
    bounds = skia.Rect(
        area.left() + _LAYOUT_INSET,
        area.top() + _LAYOUT_INSET,
        area.right() - _LAYOUT_INSET,
        area.bottom() - _LAYOUT_INSET,
    )
    cx = area.centerX()
    cy = area.centerY()
    font = font_manager.get_font(_LABEL_FONT_SIZE)
    font.setEmbolden(True)
    metrics = _label_metrics(font, names)
    radius = _fit_radius(cx, cy, metrics, bounds)
    count = len(names)
    _draw_grid(canvas, cx, cy, radius, count)

    data_points = [
        _polar(
            cx,
            cy,
            radius * (max(0, min(score, _SCORE_MAX)) / _SCORE_MAX),
            _axis_angle(i, count),
        )
        for i, score in enumerate(scores)
    ]
    _draw_data_polygon(canvas, data_points, cx, cy, radius)
    _draw_vertices(canvas, data_points)
    _draw_labels(canvas, font, names, metrics, cx, cy, radius)
