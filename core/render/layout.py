"""卡片纵向占位测算（与绘制共用公式；无 Canvas 依赖）。"""

from __future__ import annotations

import math
from typing import Callable

from models import EnemyData
from utils.wiki_skia import WikiStyle, parse_wikitext_to_spans, wrap_spans_to_lines

from core.fonts import FontManager


def measure_wiki_char(font: object, font_bold: object):
    def m(ch: str, bold: bool) -> float:
        f = font_bold if bold else font
        return f.measureText(ch)

    return m


def wiki_line_count(
    font_manager: FontManager,
    text: str,
    max_w: float,
    font_size: int,
    base: WikiStyle,
) -> int:
    fn = font_manager.get_font(font_size)
    fb = font_manager.get_font(font_size)
    fb.setEmbolden(True)
    meas = measure_wiki_char(fn, fb)
    lines = wrap_spans_to_lines(parse_wikitext_to_spans(text or "", base), max_w, meas)
    return max(1, len(lines))


COMMENT_WRAP_WIDTH = 1100
COMMENT_LINE_STEP = 45.0
COMMENT_FIRST_BASELINE = 75.0
COMMENT_LAST_BASELINE_PAD = 48.0
GRADE_BLOCK_MIN_H = 210.0


def measure_info_section(
    enemy: EnemyData, font_manager: FontManager
) -> tuple[float, float]:
    desc_base = WikiStyle(color=(1.0, 1.0, 1.0, 1.0))
    desc_lines_n = wiki_line_count(
        font_manager, enemy.brief_description or "", 1350, 33, desc_base
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
                font_manager, eff, 1410 - 850 - 30, 21, skill_gray
            )
            dynamic_height = 54 + max(0, (lines_needed - 2) * 25)
            skill_content_height += dynamic_height
    else:
        skill_content_height = 54
    talents_header_height = 45
    if enemy.talents_abilities:
        lines_needed = wiki_line_count(
            font_manager, enemy.talents_abilities, 1410 - 40, 24, skill_gray
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
    lines = wrap_text(raw, COMMENT_WRAP_WIDTH, 33) if raw else [""]
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
) -> int:
    _, info_bottom = measure_info_section(enemy, font_manager)
    skills_bottom = measure_skills_talents_bottom(enemy, info_bottom, font_manager)
    block_h = measure_grade_block_height(enemy, wrap_text)
    spacing = 28
    margin = 15
    grade_start = max(
        skills_bottom + spacing,
        float(config_height) - block_h - margin,
    )
    need = int(math.ceil(grade_start + block_h + margin))
    return max(config_height, need)
