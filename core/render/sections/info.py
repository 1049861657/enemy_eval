"""统一信息框：描述、属性表、异常抗性。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import skia

from models import EnemyData
from utils.wiki_span_parser import WikiStyle

from core.render import layout
from core.render.wiki_paragraph_renderer import draw_wiki_paragraph

if TYPE_CHECKING:
    from core.render.generator import EnemyCardGenerator


def draw_info_section(gen: "EnemyCardGenerator", enemy: EnemyData) -> float:
    desc_height, bottom_y = layout.measure_info_section(enemy, gen.font_manager)
    desc_base = WikiStyle(color=(1.0, 1.0, 1.0, 1.0))

    info_rect = skia.Rect(480, 60, 1890, bottom_y)

    bg_paint = skia.Paint(Color=skia.Color4f(0.98, 0.98, 0.98, 0.95), AntiAlias=True)
    gen.canvas.drawRect(info_rect, bg_paint)

    border_paint = skia.Paint(Color=skia.Color4f(0.8, 0.8, 0.8, 0.9), AntiAlias=True)
    border_paint.setStyle(skia.Paint.kStroke_Style)
    border_paint.setStrokeWidth(3)
    gen.canvas.drawRect(info_rect, border_paint)

    header_rect = skia.Rect(480, 60, 1890, 60 + desc_height)
    header_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)
    gen.canvas.drawRect(header_rect, header_paint)

    if desc_height > 75:
        header_bottom = skia.Rect(480, 96, 1890, 60 + desc_height - 12)
        gen.canvas.drawRect(header_bottom, header_paint)
    else:
        header_bottom = skia.Rect(480, 96, 1890, 60 + desc_height)
        gen.canvas.drawRect(header_bottom, header_paint)

    draw_wiki_paragraph(
        gen.canvas,
        gen.font_manager,
        enemy.brief_description or "",
        495,
        layout.INFO_DESC_WRAP_WIDTH,
        layout.INFO_DESC_FONT_SIZE,
        (1.0, 1.0, 1.0, 1.0),
        48,
        False,
        desc_base,
        y_first_baseline=105,
    )

    table_start_y = 60 + int(desc_height)
    _draw_stats_table(gen, enemy, table_start_y)

    resist_start_y = table_start_y + 234
    _draw_bottom_abnormal_resistances(gen, enemy, resist_start_y)

    return bottom_y


def _draw_stats_table(gen: "EnemyCardGenerator", enemy: EnemyData, start_y: int) -> None:
    attrs_data = [
        [
            ("攻击方式", enemy.attack_type),
            ("伤害类型", enemy.damage_type),
            ("行动方式", enemy.action_type),
            ("生命自回速度", enemy.hp_recovery_speed),
            ("地位", enemy.position),
            ("种类", enemy.category),
        ],
        [
            ("最大生命值", enemy.max_hp),
            ("攻击力", enemy.attack),
            ("防御力", enemy.defense),
            ("法术抗性", enemy.magic_resistance),
            ("攻击范围半径", enemy.attack_range_radius),
            ("重量", enemy.weight_level),
        ],
        [
            ("移动速度", enemy.move_speed),
            ("攻击间隔", enemy.attack_interval),
            ("损伤抗性", enemy.damage_resistance),
            ("元素抗性", enemy.element_resistance),
            ("基础嘲讽等级", enemy.base_taunt_level),
            ("目标价值", enemy.target_value),
        ],
    ]

    start_x = 480
    cell_height = 78
    total_width = 1410

    font_name = gen.font_manager.get_font(27)
    font_name.setEmbolden(True)
    font_value = gen.font_manager.get_font(30)
    name_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)
    value_paint = skia.Paint(Color=skia.Color4f(0.1, 0.1, 0.1, 1), AntiAlias=True)

    grid_paint = skia.Paint(Color=skia.Color4f(0.85, 0.85, 0.85, 1), AntiAlias=True)
    grid_paint.setStyle(skia.Paint.kStroke_Style)
    grid_paint.setStrokeWidth(1.5)

    header_bg_paint = skia.Paint(Color=skia.Color4f(0.90, 0.94, 0.98, 1), AntiAlias=True)

    for row_idx, row_data in enumerate(attrs_data):
        y = start_y + row_idx * cell_height

        row_col_width = total_width // len(row_data)

        current_x = start_x
        for col_idx, (name, value) in enumerate(row_data):
            cell_width = row_col_width
            x = current_x
            cell_rect = skia.Rect(x, y, x + cell_width, y + cell_height)

            header_cell = skia.Rect(x, y, x + cell_width, y + cell_height // 2)
            gen.canvas.drawRect(header_cell, header_bg_paint)

            gen.canvas.drawRect(cell_rect, grid_paint)

            name_width = font_name.measureText(name)
            name_x = layout.center_text_x(x, cell_width, name_width)
            gen.canvas.drawString(name, name_x, y + 30, font_name, name_paint)

            value_str = str(value)

            if (name == "种类" and value_str == "其他") or (
                name == "攻击范围半径" and value == 0
            ):
                line_paint = skia.Paint(Color=skia.Color4f(0.6, 0.6, 0.6, 1), AntiAlias=True)
                line_paint.setStyle(skia.Paint.kStroke_Style)
                line_paint.setStrokeWidth(3)

                line1 = skia.Path()
                line1.moveTo(x + 8, y + cell_height // 2 + 8)
                line1.lineTo(x + cell_width - 8, y + cell_height - 8)
                gen.canvas.drawPath(line1, line_paint)
            else:
                value_width = font_value.measureText(value_str)
                value_x = layout.center_text_x(x, cell_width, value_width)
                gen.canvas.drawString(value_str, value_x, y + 69, font_value, value_paint)

            current_x += cell_width


def _draw_bottom_abnormal_resistances(
    gen: "EnemyCardGenerator", enemy: EnemyData, start_y: int
) -> None:
    table_y = start_y
    table_height = 75

    header_width = 240
    header_rect = skia.Rect(480, table_y, 480 + header_width, table_y + table_height)

    content_rect = skia.Rect(480 + header_width, table_y, 1890, table_y + table_height)

    font = gen.font_manager.get_font(30)
    font.setEmbolden(True)
    header_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)
    text_paint = skia.Paint(Color=skia.Color4f(0.3, 0.3, 0.3, 1), AntiAlias=True)

    grid_paint = skia.Paint(Color=skia.Color4f(0.85, 0.85, 0.85, 1), AntiAlias=True)
    grid_paint.setStyle(skia.Paint.kStroke_Style)
    grid_paint.setStrokeWidth(1.5)

    header_bg_paint = skia.Paint(Color=skia.Color4f(0.90, 0.94, 0.98, 1), AntiAlias=True)
    gen.canvas.drawRect(header_rect, header_bg_paint)

    gen.canvas.drawRect(header_rect, grid_paint)
    gen.canvas.drawRect(content_rect, grid_paint)

    separator_x = 480 + header_width
    separator_line = skia.Path()
    separator_line.moveTo(separator_x, table_y)
    separator_line.lineTo(separator_x, table_y + table_height)
    gen.canvas.drawPath(separator_line, grid_paint)

    gen.canvas.drawString("异常抗性", 510, table_y + 48, font, header_paint)

    active_resistances = []
    for resistance_name, value in enemy.abnormal_resistances.items():
        if value == 1:
            active_resistances.append(resistance_name)

    if active_resistances:
        resist_text = " · ".join(active_resistances)
    else:
        resist_text = "无"

    gen.canvas.drawString(
        resist_text, 480 + header_width + 30, table_y + 48, font, text_paint
    )
