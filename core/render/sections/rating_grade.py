"""左侧评价区（星级记分板 / 雷达图）与底部等级+简评。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import skia

from models import EnemyData, RenderOptions

from .. import layout
from ..fonts import FontManager
from ..primitives.radar import draw_rating_radar
from ..primitives.stars import draw_star

if TYPE_CHECKING:
    from core.render.generator import EnemyCardGenerator

# 记分板配色：深色底板 + 单一琥珀强调色，与信息区深色表头同一语言
_PANEL_TOP = (0.113, 0.125, 0.149)
_PANEL_BOTTOM = (0.067, 0.075, 0.094)
_HEADER_FILL = (0.043, 0.051, 0.067)
_ACCENT = (0.988, 0.749, 0.286)
_STAR_TRACK = (0.192, 0.212, 0.251)
_TITLE_COLOR = (0.957, 0.969, 0.988)
_LATIN_COLOR = (0.478, 0.529, 0.608)
_NAME_COLOR = (0.851, 0.878, 0.925)
_WHITE = (1.0, 1.0, 1.0)

_TITLE_FONT_SIZE = 26
_LATIN_FONT_SIZE = 15
_LATIN_TRACKING = 3.4
_NAME_FONT_SIZE_MAX = 24
_NAME_FONT_SIZE_MIN = 17
_STAR_RADIUS = 12.5
_STAR_PITCH = 30.0
_STAR_MAX = 5
_PAD_X = 22.0
_TICK_WIDTH = 3.0
_TICK_HEIGHT = 18.0
_TICK_GAP = 11.0
_BRACKET_LEG = 22.0


def _fill(color: tuple[float, float, float], alpha: float = 1.0) -> skia.Paint:
    return skia.Paint(Color=skia.Color4f(*color, alpha), AntiAlias=True)


def _stroke(
    color: tuple[float, float, float], alpha: float, width: float
) -> skia.Paint:
    paint = skia.Paint(Color=skia.Color4f(*color, alpha), AntiAlias=True)
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(width)
    paint.setStrokeJoin(skia.Paint.kMiter_Join)
    return paint


def _panel_path(rect: skia.Rect, notch: float) -> skia.Path:
    """左上 / 右下切角的面板轮廓。"""
    path = skia.Path()
    path.moveTo(rect.left() + notch, rect.top())
    path.lineTo(rect.right(), rect.top())
    path.lineTo(rect.right(), rect.bottom() - notch)
    path.lineTo(rect.right() - notch, rect.bottom())
    path.lineTo(rect.left(), rect.bottom())
    path.lineTo(rect.left(), rect.top() + notch)
    path.close()
    return path


def _tracked_width(text: str, font: skia.Font, tracking: float) -> float:
    if not text:
        return 0.0
    return sum(font.measureText(ch) for ch in text) + tracking * (len(text) - 1)


def _draw_tracked_text(
    canvas: skia.Canvas,
    text: str,
    x: float,
    baseline: float,
    font: skia.Font,
    paint: skia.Paint,
    tracking: float,
) -> None:
    cursor = x
    for ch in text:
        canvas.drawString(ch, cursor, baseline, font, paint)
        cursor += font.measureText(ch) + tracking


def _fit_name_font(
    font_manager: FontManager, names: list[str], limit: float
) -> tuple[skia.Font, int]:
    """取能让最长维度名放进 limit 的最大字号，保证各行字号一致。"""
    for size in range(_NAME_FONT_SIZE_MAX, _NAME_FONT_SIZE_MIN, -1):
        font = font_manager.get_font(size)
        font.setEmbolden(True)
        if all(font.measureText(name) <= limit for name in names):
            return font, size
    font = font_manager.get_font(_NAME_FONT_SIZE_MIN)
    font.setEmbolden(True)
    return font, _NAME_FONT_SIZE_MIN


def _draw_panel_chrome(canvas: skia.Canvas, path: skia.Path, rect: skia.Rect) -> None:
    shadow = _fill((0.0, 0.02, 0.08), 0.32)
    shadow.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 9.0))
    canvas.save()
    canvas.translate(0.0, 7.0)
    canvas.drawPath(path, shadow)
    canvas.restore()

    body = skia.Paint(AntiAlias=True)
    body.setShader(
        skia.GradientShader.MakeLinear(
            points=[(rect.left(), rect.top()), (rect.left(), rect.bottom())],
            colors=[
                skia.Color4f(*_PANEL_TOP, 1.0),
                skia.Color4f(*_PANEL_BOTTOM, 1.0),
            ],
        )
    )
    canvas.drawPath(path, body)
    canvas.drawPath(path, _stroke(_WHITE, 0.10, 1.6))

    # 切角在左上 / 右下，角标补在另一条对角线上，构成对称的 HUD 轮廓
    brackets = skia.Path()
    inset = 1.4
    left = rect.left() + inset
    right = rect.right() - inset
    top = rect.top() + inset
    bottom = rect.bottom() - inset
    brackets.moveTo(right - _BRACKET_LEG, top)
    brackets.lineTo(right, top)
    brackets.lineTo(right, top + _BRACKET_LEG)
    brackets.moveTo(left, bottom - _BRACKET_LEG)
    brackets.lineTo(left, bottom)
    brackets.lineTo(left + _BRACKET_LEG, bottom)
    canvas.drawPath(brackets, _stroke(_ACCENT, 0.85, 2.6))


def _draw_panel_header(
    canvas: skia.Canvas,
    font_manager: FontManager,
    path: skia.Path,
    rect: skia.Rect,
    header_h: float,
) -> None:
    canvas.save()
    canvas.clipPath(path, skia.ClipOp.kIntersect, True)
    canvas.drawRect(
        skia.Rect(rect.left(), rect.top(), rect.right(), rect.top() + header_h),
        _fill(_HEADER_FILL),
    )
    canvas.drawRect(
        skia.Rect(
            rect.left(),
            rect.top() + header_h - 2.0,
            rect.right(),
            rect.top() + header_h,
        ),
        _fill(_ACCENT, 0.9),
    )
    canvas.drawRect(
        skia.Rect(
            rect.left(),
            rect.top() + 18.0,
            rect.left() + 5.0,
            rect.top() + header_h - 18.0,
        ),
        _fill(_ACCENT),
    )
    canvas.restore()

    mid = rect.top() + header_h / 2.0
    title_font = font_manager.get_font(_TITLE_FONT_SIZE)
    title_font.setEmbolden(True)
    canvas.drawString(
        "评价维度",
        rect.left() + _PAD_X,
        mid + _TITLE_FONT_SIZE * 0.36,
        title_font,
        _fill(_TITLE_COLOR),
    )

    latin_font = font_manager.get_font(_LATIN_FONT_SIZE)
    latin_font.setEmbolden(True)
    latin_w = _tracked_width("RATING", latin_font, _LATIN_TRACKING)
    _draw_tracked_text(
        canvas,
        "RATING",
        rect.right() - _PAD_X - latin_w,
        mid + _LATIN_FONT_SIZE * 0.36,
        latin_font,
        _fill(_LATIN_COLOR),
        _LATIN_TRACKING,
    )


def _draw_rating_panel(
    gen: "EnemyCardGenerator", names: list[str], scores: list[int]
) -> None:
    canvas = gen.canvas
    header_h = float(layout.RATING_PANEL_HEADER_H)
    row_h = float(layout.RATING_PANEL_ROW_H)
    pad_y = float(layout.RATING_PANEL_PAD_Y)
    left = float(layout.RATING_PANEL_X)
    top = float(layout.RATING_SECTION_TOP)
    rect = skia.Rect(
        left,
        top,
        left + float(layout.RATING_PANEL_WIDTH),
        top + header_h + pad_y * 2.0 + len(names) * row_h,
    )
    path = _panel_path(rect, float(layout.RATING_PANEL_NOTCH))

    _draw_panel_chrome(canvas, path, rect)
    _draw_panel_header(canvas, gen.font_manager, path, rect, header_h)

    stars_span = (_STAR_MAX - 1) * _STAR_PITCH + 2.0 * _STAR_RADIUS
    first_star_cx = rect.right() - _PAD_X - stars_span + _STAR_RADIUS
    name_x = rect.left() + _PAD_X + _TICK_WIDTH + _TICK_GAP
    name_font, name_size = _fit_name_font(
        gen.font_manager,
        names,
        first_star_cx - _STAR_RADIUS - name_x - 14.0,
    )
    name_paint = _fill(_NAME_COLOR)
    name_baseline_offset = name_size * 0.36
    divider = _stroke(_WHITE, 0.07, 1.0)

    row_top = rect.top() + header_h + pad_y
    for i, (name, score) in enumerate(zip(names, scores)):
        mid = row_top + row_h / 2.0
        if i > 0:
            canvas.drawLine(
                rect.left() + _PAD_X, row_top, rect.right() - _PAD_X, row_top, divider
            )

        canvas.drawRect(
            skia.Rect(
                rect.left() + _PAD_X,
                mid - _TICK_HEIGHT / 2.0,
                rect.left() + _PAD_X + _TICK_WIDTH,
                mid + _TICK_HEIGHT / 2.0,
            ),
            _fill(layout.rating_color_at(i)),
        )
        canvas.drawString(
            name, name_x, mid + name_baseline_offset, name_font, name_paint
        )

        for j in range(_STAR_MAX):
            cx = first_star_cx + j * _STAR_PITCH
            if j < score:
                draw_star(canvas, cx, mid, _STAR_RADIUS, _ACCENT, glow=1.0)
            else:
                draw_star(canvas, cx, mid, _STAR_RADIUS, _STAR_TRACK)

        row_top += row_h


def draw_rating_section(
    gen: "EnemyCardGenerator", enemy: EnemyData, options: RenderOptions
) -> None:
    names = [item.name for item in enemy.ratings]
    if not names:
        return
    scores = [item.score for item in enemy.ratings]
    if options.rating_radar:
        draw_rating_radar(gen.canvas, gen.font_manager, names, scores)
        return
    _draw_rating_panel(gen, names, scores)


def draw_grade_section(
    gen: "EnemyCardGenerator",
    enemy: EnemyData,
    options: RenderOptions,
    skills_bottom_y: float,
) -> None:
    block_h = layout.measure_grade_block_height(enemy, gen._wrap_text)
    spacing = 28
    margin = 15
    names = [item.name for item in enemy.ratings]
    left_floor = float(skills_bottom_y)
    if names:
        left_floor = max(
            left_floor,
            layout.measure_rating_section_bottom(
                len(names), radar=options.rating_radar
            ),
        )
    content_floor = left_floor + spacing
    grade_start_y = max(
        content_floor,
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
