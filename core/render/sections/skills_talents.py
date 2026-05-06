"""技能与天赋表格。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import skia

from models import EnemyData
from utils.wiki_skia import WikiStyle

from core.render import layout
from core.render.wiki_text import draw_wiki_paragraph

if TYPE_CHECKING:
    from core.render.generator import EnemyCardGenerator


def draw_skills_talents_section(
    gen: "EnemyCardGenerator", enemy: EnemyData, start_y: int = 460
) -> float:
    section_y = start_y + 20
    table_start_x = 480
    table_width = 1410
    _draw_skills_talents_table(gen, enemy, table_start_x, section_y, table_width)
    return layout.measure_skills_talents_bottom(enemy, float(start_y), gen.font_manager)


def _draw_skills_talents_table(
    gen: "EnemyCardGenerator",
    enemy: EnemyData,
    start_x: int,
    start_y: int,
    width: int,
) -> None:
    skill_title_header_height = 45
    skill_column_header_height = 45
    skill_row_height = 54
    skill_rows = len(enemy.skills) if enemy.skills else 1
    skills_content_height = skill_rows * skill_row_height

    talents_header_height = 45

    skill_gray = WikiStyle(color=(0.3, 0.3, 0.3, 1.0))
    if enemy.talents_abilities:
        lines_needed = layout.wiki_line_count(
            gen.font_manager,
            enemy.talents_abilities,
            width - 40,
            24,
            skill_gray,
        )
        talents_content_height = 50 + lines_needed * 28
    else:
        talents_content_height = 90

    border_paint = skia.Paint(Color=skia.Color4f(0.7, 0.7, 0.7, 1), AntiAlias=True)
    border_paint.setStyle(skia.Paint.kStroke_Style)
    border_paint.setStrokeWidth(2)

    current_y = start_y
    _draw_skills_title_header(
        gen, start_x, current_y, width, skill_title_header_height, border_paint
    )

    skills_table_y = current_y + skill_title_header_height
    _draw_skills_section(
        gen,
        enemy,
        start_x,
        skills_table_y,
        width,
        skill_column_header_height,
        skills_content_height,
    )

    skill_gray = WikiStyle(color=(0.3, 0.3, 0.3, 1.0))
    dynamic_skills_content_height = 0
    if enemy.skills:
        for skill in enemy.skills:
            eff = skill.效果 or "无效果"
            lines_needed = layout.wiki_line_count(
                gen.font_manager,
                eff,
                width - 850 - 30,
                21,
                skill_gray,
            )
            dynamic_height = 54 + max(0, (lines_needed - 2) * 25)
            dynamic_skills_content_height += dynamic_height
    else:
        dynamic_skills_content_height = 54

    talents_start_y = skills_table_y + skill_column_header_height + dynamic_skills_content_height
    _draw_talents_section(
        gen,
        enemy,
        start_x,
        talents_start_y,
        width,
        talents_header_height,
        talents_content_height,
        border_paint,
    )


def _draw_skills_title_header(
    gen: "EnemyCardGenerator",
    start_x: int,
    start_y: int,
    width: int,
    header_height: int,
    border_paint: skia.Paint,
) -> None:
    table_bg_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 0.9), AntiAlias=True)
    header_rect = skia.Rect(start_x, start_y, start_x + width, start_y + header_height)
    gen.canvas.drawRect(header_rect, table_bg_paint)
    gen.canvas.drawRect(header_rect, border_paint)

    header_bg_paint = skia.Paint(Color=skia.Color4f(0.9, 0.9, 0.9, 1), AntiAlias=True)
    gen.canvas.drawRect(header_rect, header_bg_paint)

    header_line_top = skia.Path()
    header_line_top.moveTo(start_x, start_y)
    header_line_top.lineTo(start_x + width, start_y)
    gen.canvas.drawPath(header_line_top, border_paint)

    header_line_bottom = skia.Path()
    header_line_bottom.moveTo(start_x, start_y + header_height)
    header_line_bottom.lineTo(start_x + width, start_y + header_height)
    gen.canvas.drawPath(header_line_bottom, border_paint)

    font_header = gen.font_manager.get_font(24)
    font_header.setEmbolden(True)
    header_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)
    skill_title_text = "技能"
    skill_title_width = font_header.measureText(skill_title_text)
    skill_title_x = start_x + (width - skill_title_width) / 2
    gen.canvas.drawString(
        skill_title_text, skill_title_x, start_y + 30, font_header, header_paint
    )


def _draw_skills_section(
    gen: "EnemyCardGenerator",
    enemy: EnemyData,
    start_x: int,
    start_y: int,
    width: int,
    header_height: int,
    content_height: int,
) -> None:
    base_row_height = 54
    col_widths = [350, 250, 250, width - 850]

    skill_gray = WikiStyle(color=(0.3, 0.3, 0.3, 1.0))
    skill_row_heights = []
    if enemy.skills:
        for skill in enemy.skills:
            eff = skill.效果 or "无效果"
            lines_needed = layout.wiki_line_count(
                gen.font_manager,
                eff,
                col_widths[3] - 30,
                21,
                skill_gray,
            )
            dynamic_height = base_row_height + max(0, (lines_needed - 2) * 25)
            skill_row_heights.append(dynamic_height)
    else:
        skill_row_heights = [base_row_height]

    font_header = gen.font_manager.get_font(24)
    font_header.setEmbolden(True)
    font_content = gen.font_manager.get_font(21)
    header_paint = skia.Paint(Color=skia.Color4f(0.1, 0.1, 0.1, 1), AntiAlias=True)
    content_paint = skia.Paint(Color=skia.Color4f(0.3, 0.3, 0.3, 1), AntiAlias=True)

    border_paint = skia.Paint(Color=skia.Color4f(0.7, 0.7, 0.7, 1), AntiAlias=True)
    border_paint.setStyle(skia.Paint.kStroke_Style)
    border_paint.setStrokeWidth(2)

    grid_paint = skia.Paint(Color=skia.Color4f(0.7, 0.7, 0.7, 1), AntiAlias=True)
    grid_paint.setStyle(skia.Paint.kStroke_Style)
    grid_paint.setStrokeWidth(1)

    if enemy.skills:
        dynamic_content_height = sum(skill_row_heights)
        total_height = header_height + dynamic_content_height
        table_rect = skia.Rect(start_x, start_y, start_x + width, start_y + total_height)
        table_bg_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 0.9), AntiAlias=True)
        gen.canvas.drawRect(table_rect, table_bg_paint)
        gen.canvas.drawRect(table_rect, border_paint)

        header_bg_paint = skia.Paint(Color=skia.Color4f(0.95, 0.95, 0.95, 1), AntiAlias=True)
        header_rect = skia.Rect(start_x, start_y, start_x + width, start_y + header_height)
        gen.canvas.drawRect(header_rect, header_bg_paint)

        header_line_top = skia.Path()
        header_line_top.moveTo(start_x, start_y)
        header_line_top.lineTo(start_x + width, start_y)
        gen.canvas.drawPath(header_line_top, border_paint)

        header_line_bottom = skia.Path()
        header_line_bottom.moveTo(start_x, start_y + header_height)
        header_line_bottom.lineTo(start_x + width, start_y + header_height)
        gen.canvas.drawPath(header_line_bottom, border_paint)

        headers = ["名称", "冷却时间", "技力消耗", "效果"]
        current_x = start_x
        for i, header in enumerate(headers):
            text_x = current_x + col_widths[i] / 2 - font_header.measureText(header) / 2
            gen.canvas.drawString(header, text_x, start_y + 30, font_header, header_paint)

            if i < len(headers) - 1:
                line_x = current_x + col_widths[i]
                line = skia.Path()
                line.moveTo(line_x, start_y)
                line.lineTo(line_x, start_y + header_height + dynamic_content_height)
                gen.canvas.drawPath(line, grid_paint)

            current_x += col_widths[i]

        content_start_y = start_y + header_height
        current_row_y = content_start_y
        for i, skill in enumerate(enemy.skills):
            row_height = skill_row_heights[i]
            row_y = current_row_y
            current_x = start_x

            if i > 0:
                row_line = skia.Path()
                row_line.moveTo(start_x, row_y)
                row_line.lineTo(start_x + width, row_y)
                gen.canvas.drawPath(row_line, grid_paint)

            draw_wiki_paragraph(
                gen.canvas,
                gen.font_manager,
                skill.名称 or "未知",
                current_x + 8,
                col_widths[0] - 16,
                21,
                (0.3, 0.3, 0.3, 1.0),
                22,
                True,
                skill_gray,
                cell_vertical=(row_y, row_height),
            )
            current_x += col_widths[0]

            cooldown = skill.冷却时间 or "无"
            cooldown_x = (
                current_x + col_widths[1] / 2 - font_content.measureText(cooldown) / 2
            )
            cooldown_y = row_y + row_height / 2 + 5
            gen.canvas.drawString(cooldown, cooldown_x, cooldown_y, font_content, content_paint)
            current_x += col_widths[1]

            cost = skill.技力消耗 or "0"
            cost_y = row_y + row_height / 2 + 5
            cell_cx = current_x + col_widths[2] / 2
            if not cost or cost == "0" or cost.strip() == "":
                ph_font = gen.font_manager.get_font(20)
                placeholder = "—"
                ph_paint = skia.Paint(
                    Color=skia.Color4f(0.62, 0.64, 0.68, 0.92), AntiAlias=True
                )
                tw = ph_font.measureText(placeholder)
                gen.canvas.drawString(
                    placeholder, cell_cx - tw / 2, cost_y, ph_font, ph_paint
                )
            else:
                cost_x = cell_cx - font_content.measureText(cost) / 2
                gen.canvas.drawString(cost, cost_x, cost_y, font_content, content_paint)
            current_x += col_widths[2]

            draw_wiki_paragraph(
                gen.canvas,
                gen.font_manager,
                skill.效果 or "无效果",
                current_x + 15,
                col_widths[3] - 30,
                21,
                (0.3, 0.3, 0.3, 1.0),
                25,
                True,
                skill_gray,
                cell_vertical=(row_y, row_height),
            )

            current_row_y += row_height
    else:
        simple_height = 60
        simple_rect = skia.Rect(start_x, start_y, start_x + width, start_y + simple_height)
        table_bg_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 0.9), AntiAlias=True)
        gen.canvas.drawRect(simple_rect, table_bg_paint)
        gen.canvas.drawRect(simple_rect, border_paint)

        no_skill_text = "无特殊技能"
        no_skill_width = font_content.measureText(no_skill_text)
        no_skill_x = start_x + (width - no_skill_width) / 2
        gen.canvas.drawString(no_skill_text, no_skill_x, start_y + 38, font_content, content_paint)


def _draw_talents_section(
    gen: "EnemyCardGenerator",
    enemy: EnemyData,
    start_x: int,
    start_y: int,
    width: int,
    header_height: int,
    content_height: int,
    border_paint: skia.Paint,
) -> None:
    total_height = header_height + content_height
    table_rect = skia.Rect(start_x, start_y, start_x + width, start_y + total_height)
    table_bg_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 0.9), AntiAlias=True)
    gen.canvas.drawRect(table_rect, table_bg_paint)
    gen.canvas.drawRect(table_rect, border_paint)

    header_bg_paint = skia.Paint(Color=skia.Color4f(0.9, 0.9, 0.9, 1), AntiAlias=True)
    header_rect = skia.Rect(start_x, start_y, start_x + width, start_y + header_height)
    gen.canvas.drawRect(header_rect, header_bg_paint)

    header_line = skia.Path()
    header_line.moveTo(start_x, start_y)
    header_line.lineTo(start_x + width, start_y)
    gen.canvas.drawPath(header_line, border_paint)

    header_line2 = skia.Path()
    header_line2.moveTo(start_x, start_y + header_height)
    header_line2.lineTo(start_x + width, start_y + header_height)
    gen.canvas.drawPath(header_line2, border_paint)

    talents_font = gen.font_manager.get_font(24)
    talents_font.setEmbolden(True)
    talents_title_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)
    talent_title_text = "天赋&能力"
    talent_title_width = talents_font.measureText(talent_title_text)
    talent_title_x = start_x + (width - talent_title_width) / 2
    gen.canvas.drawString(
        talent_title_text, talent_title_x, start_y + 30, talents_font, talents_title_paint
    )

    content_start_y = start_y + header_height
    if enemy.talents_abilities:
        draw_wiki_paragraph(
            gen.canvas,
            gen.font_manager,
            enemy.talents_abilities,
            start_x + 20,
            width - 40,
            24,
            (0.3, 0.3, 0.3, 1.0),
            28,
            True,
            WikiStyle(color=(0.3, 0.3, 0.3, 1.0)),
            y_first_baseline=content_start_y + 25,
        )
    else:
        no_talent_font = gen.font_manager.get_font(24)
        no_talent_paint = skia.Paint(Color=skia.Color4f(0.5, 0.5, 0.5, 1), AntiAlias=True)
        no_talent_text = "无特殊天赋能力"
        no_talent_width = no_talent_font.measureText(no_talent_text)
        no_talent_x = start_x + (width - no_talent_width) / 2
        gen.canvas.drawString(
            no_talent_text, no_talent_x, content_start_y + 50, no_talent_font, no_talent_paint
        )
