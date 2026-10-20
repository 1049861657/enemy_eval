"""wikitext 片段绘制：把 `wikitext_spans` 解析出的片段按行画到 Skia 画布。

换行与占位宽度一律复用 `wikitext_spans` 的常量与 `wrap_spans_to_lines`，本模块不另立口径；
只画不解析模板语法（PRTS 模板语法的数据源侧解析见 `utils/prts/wikitext_templates.py`）。
"""

from __future__ import annotations

import skia

from .wikitext_spans import (
    TextSpan,
    WikiStyle,
    hint_mark_advance,
    parse_wikitext_to_spans,
    wrap_spans_to_lines,
)

from ..fonts import FontManager
from ..layout import build_wiki_measurer


def _span_draw_width(
    sp: TextSpan, fn: skia.Font, fb: skia.Font, font_size: int
) -> float:
    if sp.style.hint:
        return hint_mark_advance(font_size) * len(sp.text)
    fnt = fb if sp.style.bold else fn
    return fnt.measureText(sp.text)


def _draw_help_circle_outline(
    canvas: skia.Canvas,
    font_manager: FontManager,
    x: float,
    baseline_y: float,
    font_size: int,
    color: tuple[float, float, float, float],
) -> float:
    """对应 PRTS 模板:Popup 默认图标 mdi-help-circle-outline，无交互。"""
    advance = hint_mark_advance(font_size)
    cx = x + advance / 2.0
    cy = baseline_y - font_size * 0.32
    radius = advance * 0.42
    ring = skia.Paint(Color=skia.Color4f(*color), AntiAlias=True)
    ring.setStyle(skia.Paint.kStroke_Style)
    ring.setStrokeWidth(max(1.15, font_size / 15.0))
    canvas.drawCircle(cx, cy, radius, ring)

    q_size = max(10, int(round(font_size * 0.58)))
    q_font = font_manager.get_font(q_size)
    q_font.setEmbolden(True)
    glyph = "?"
    qw = q_font.measureText(glyph)
    q_baseline = cy + q_size * 0.36
    paint = skia.Paint(Color=skia.Color4f(*color), AntiAlias=True)
    canvas.drawString(glyph, cx - qw / 2.0, q_baseline, q_font, paint)
    return x + advance


def draw_wiki_paragraph(
    canvas: skia.Canvas,
    font_manager: FontManager,
    text: str,
    x_left: float,
    max_width: float,
    font_size: int,
    default_rgbaf: tuple[float, float, float, float],
    line_step: float,
    center: bool,
    base: WikiStyle,
    *,
    y_first_baseline: float | None = None,
    cell_vertical: tuple[float, float] | None = None,
) -> float:
    fn, fb, meas = build_wiki_measurer(font_manager, font_size)
    lines = wrap_spans_to_lines(parse_wikitext_to_spans(text or "", base), max_width, meas)
    if cell_vertical is not None:
        cy, ch = cell_vertical
        n = max(len(lines), 1)
        block_h = (n - 1) * line_step + line_step * 0.82
        y = cy + max((ch - block_h) / 2.0 + line_step * 0.74, line_step * 0.88)
    elif y_first_baseline is not None:
        y = y_first_baseline
    else:
        y = 0.0
    for line in lines:
        tw = sum(_span_draw_width(sp, fn, fb, font_size) for sp in line)
        x0 = x_left + (max_width - tw) / 2 if center else x_left
        x = x0
        for sp in line:
            if sp.style.hint:
                color = sp.style.color or default_rgbaf
                for _ in sp.text:
                    x = _draw_help_circle_outline(
                        canvas, font_manager, x, y, font_size, color
                    )
                continue
            fnt = fb if sp.style.bold else fn
            if sp.style.dim:
                c = (0.55, 0.55, 0.55, 1.0)
            elif sp.style.color:
                c = sp.style.color
            else:
                c = default_rgbaf
            paint = skia.Paint(Color=skia.Color4f(*c), AntiAlias=True)
            canvas.drawString(sp.text, x, y, fnt, paint)
            if sp.style.underline:
                uw = fnt.measureText(sp.text)
                ly = y + max(3.0, font_size * 0.12)
                ul = skia.Path()
                ul.moveTo(x, ly)
                ul.lineTo(x + uw, ly)
                ul_paint = skia.Paint(Color=skia.Color4f(*c), AntiAlias=True)
                ul_paint.setStyle(skia.Paint.kStroke_Style)
                ul_paint.setStrokeWidth(max(1.0, font_size / 18.0))
                canvas.drawPath(ul, ul_paint)
            x += fnt.measureText(sp.text)
        y += line_step
    return y
