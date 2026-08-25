"""卡片纵向占位测算（与绘制共用公式；无 Canvas 依赖）。"""

from __future__ import annotations

import math
from typing import Callable

from models import EnemyData
from utils.wiki_span_parser import (
    WikiStyle,
    hint_mark_advance,
    parse_wikitext_to_spans,
    wrap_spans_to_lines,
)

from core.fonts import FontManager


def measure_wiki_char(font: object, font_bold: object, font_size: int):
    def m(ch: str, style: WikiStyle) -> float:
        if style.hint:
            return hint_mark_advance(font_size)
        f = font_bold if style.bold else font
        return f.measureText(ch)

    return m


def build_wiki_measurer(font_manager: FontManager, font_size: int):
    """构造 wiki 富文本绘制/测量共用的一组字体与逐字符测量函数。

    返回 `(fn, fb, meas)`：`fn` 为常规字体、`fb` 为同 size 的粗体字体（各自
    独立实例，互不干扰），`meas` 为绑定了这两个字体的逐字符测量闭包
    （见 `measure_wiki_char`）。`core/render/wiki_paragraph_renderer.py::draw_wiki_paragraph`
    与本模块的 `wiki_line_count` 共用此函数，避免测量口径与绘制口径各自
    手写同一段样板代码而漂移。
    """
    fn = font_manager.get_font(font_size)
    fb = font_manager.get_font(font_size)
    fb.setEmbolden(True)
    meas = measure_wiki_char(fn, fb, font_size)
    return fn, fb, meas


def darken(color: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    """按固定系数把 RGB 三分量整体调暗，返回新的三元组（不含 alpha，由调用方自行指定）。"""
    return (color[0] * factor, color[1] * factor, color[2] * factor)


def center_text_x(x: float, width: float, text_width: float) -> float:
    """容器起点 x、容器宽度 width 内，宽度为 text_width 的文本居中对齐的起始横坐标。"""
    return x + (width - text_width) / 2


def wiki_line_count(
    font_manager: FontManager,
    text: str,
    max_w: float,
    font_size: int,
    base: WikiStyle,
) -> int:
    _, _, meas = build_wiki_measurer(font_manager, font_size)
    lines = wrap_spans_to_lines(parse_wikitext_to_spans(text or "", base), max_w, meas)
    return max(1, len(lines))


INFO_DESC_WRAP_WIDTH = 1350
INFO_DESC_FONT_SIZE = 33
SKILL_EFFECT_WRAP_WIDTH = 1410 - 850 - 30
SKILL_EFFECT_FONT_SIZE = 21
TALENTS_TEXT_WRAP_WIDTH = 1410 - 40
TALENTS_TEXT_FONT_SIZE = 24
GRADE_COMMENT_FONT_SIZE = 33

COMMENT_WRAP_WIDTH = 1100
COMMENT_LINE_STEP = 45.0
COMMENT_FIRST_BASELINE = 75.0
COMMENT_LAST_BASELINE_PAD = 48.0
GRADE_BLOCK_MIN_H = 210.0

# 左侧评价卡布局（与 rating_grade.draw_rating_cards 共用）
RATING_CARD_START_X = 60
RATING_CARD_START_Y = 560
RATING_CARD_WIDTH = 360
RATING_CARD_HEIGHT = 105
RATING_CARD_SPACING = 126
RATING_PALETTE: tuple[tuple[float, float, float], ...] = (
    (0.85, 0.2, 0.3),   # 红
    (0.2, 0.6, 0.9),    # 蓝
    (0.9, 0.5, 0.1),    # 橙
    (0.35, 0.7, 0.35),  # 绿
    (0.55, 0.35, 0.75), # 紫
)


def rating_color_at(index: int) -> tuple[float, float, float]:
    return RATING_PALETTE[index % len(RATING_PALETTE)]


def measure_rating_section_bottom(dimension_count: int) -> float:
    """左侧评价卡区域底边 y；0 条时返回起点（不占位）。"""
    n = max(0, dimension_count)
    if n <= 0:
        return float(RATING_CARD_START_Y)
    return float(
        RATING_CARD_START_Y + (n - 1) * RATING_CARD_SPACING + RATING_CARD_HEIGHT
    )


def measure_info_section(
    enemy: EnemyData, font_manager: FontManager
) -> tuple[float, float]:
    desc_base = WikiStyle(color=(1.0, 1.0, 1.0, 1.0))
    desc_lines_n = wiki_line_count(
        font_manager,
        enemy.brief_description or "",
        INFO_DESC_WRAP_WIDTH,
        INFO_DESC_FONT_SIZE,
        desc_base,
    )
    desc_height = max(75, desc_lines_n * 48 + 30)
    total_height = desc_height + 234 + 75
    return float(desc_height), 60.0 + float(total_height)


def measure_skills_talents_bottom(
    enemy: EnemyData,
    info_section_bottom: float,
    font_manager: FontManager,
) -> float:
    section_y = info_section_bottom + 20
    skill_title_header_height = 45
    skill_column_header_height = 45
    skill_gray = WikiStyle(color=(0.3, 0.3, 0.3, 1.0))
    skill_content_height = 0
    if enemy.skills:
        for skill in enemy.skills:
            eff = skill.效果 or "无效果"
            lines_needed = wiki_line_count(
                font_manager, eff, SKILL_EFFECT_WRAP_WIDTH, SKILL_EFFECT_FONT_SIZE, skill_gray
            )
            dynamic_height = 54 + max(0, (lines_needed - 2) * 25)
            skill_content_height += dynamic_height
    else:
        skill_content_height = 54
    talents_header_height = 45
    if enemy.talents_abilities:
        lines_needed = wiki_line_count(
            font_manager,
            enemy.talents_abilities,
            TALENTS_TEXT_WRAP_WIDTH,
            TALENTS_TEXT_FONT_SIZE,
            skill_gray,
        )
        talents_content_height = 50 + lines_needed * 28
    else:
        talents_content_height = 90
    unified_table_height = (
        skill_title_header_height
        + skill_column_header_height
        + skill_content_height
        + talents_header_height
        + talents_content_height
    )
    section_height = unified_table_height + 30
    return section_y + section_height


def measure_grade_block_height(
    enemy: EnemyData,
    wrap_text: Callable[[str, int, int], list[str]],
) -> float:
    raw = (enemy.brief_comment or "").strip()
    lines = wrap_text(raw, COMMENT_WRAP_WIDTH, GRADE_COMMENT_FONT_SIZE) if raw else [""]
    n = max(1, len(lines))
    content_h = (
        COMMENT_FIRST_BASELINE
        + (n - 1) * COMMENT_LINE_STEP
        + COMMENT_LAST_BASELINE_PAD
    )
    return float(max(GRADE_BLOCK_MIN_H, content_h))


def measure_render_height(
    enemy: EnemyData,
    config_height: int,
    font_manager: FontManager,
    wrap_text: Callable[[str, int, int], list[str]],
    rating_dimension_count: int = 0,
) -> int:
    _, info_bottom = measure_info_section(enemy, font_manager)
    skills_bottom = measure_skills_talents_bottom(enemy, info_bottom, font_manager)
    rating_bottom = measure_rating_section_bottom(rating_dimension_count)
    block_h = measure_grade_block_height(enemy, wrap_text)
    spacing = 28
    margin = 15
    # 等级块不得压住左侧评价卡 / 技能区
    left_floor = skills_bottom
    if rating_dimension_count > 0:
        left_floor = max(left_floor, rating_bottom)
    content_floor = left_floor + spacing
    grade_start = max(
        content_floor,
        float(config_height) - block_h - margin,
    )
    need = int(math.ceil(grade_start + block_h + margin))
    return max(config_height, need)
