"""Wikitext 段落绘制（Skia）。"""

from __future__ import annotations

import skia

from utils.wiki_span_parser import WikiStyle, parse_wikitext_to_spans, wrap_spans_to_lines

from core.fonts import FontManager

from .layout import build_wiki_measurer


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
        tw = sum((fb if sp.style.bold else fn).measureText(sp.text) for sp in line)
        x0 = x_left + (max_width - tw) / 2 if center else x_left
        x = x0
        for sp in line:
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
