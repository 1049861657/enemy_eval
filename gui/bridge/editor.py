"""编辑域：卡片字段写入、抗性、评价分数、维度模板套用、雷达开关、头像选择。

写入一律经 `gui/card_model.py::CardModel`（撤销栈的唯一入口）；本模块只做输入解析、
校验与错误文案，不直接碰 QML。
"""

from __future__ import annotations

import json
from typing import Callable, TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog, QWidget

from models import RatingSchema, scores_for_rating_draft
from utils.app.rating_prefs import save_rating_schema
from utils.app.render_prefs import (
    current_render_options,
    is_rating_radar,
    set_rating_radar,
)
from utils.errors import FileOperationError

if TYPE_CHECKING:
    from gui.card_model import CardModel
    from gui.render_coordinator import RenderCoordinator

FieldError = Callable[[str, str], None]
"""字段错误回调：(字段名, 文案) → 界面提示。"""


def enemy_data_json(card_model: CardModel) -> str:
    """当前卡数据的 JSON；排除 `skills`（技能列表走 SkillListModel）。"""
    return card_model.enemy_data.model_dump_json(ensure_ascii=False, exclude={"skills"})


def update_property(
    card_model: CardModel, property_name: str, value_json: str, on_error: FieldError
) -> None:
    """按 JSON 标量更新单个字段；解析失败发字段错误。"""
    try:
        value = json.loads(value_json)
    except json.JSONDecodeError:
        on_error(property_name, "输入格式无效")
        return
    card_model.update_property(property_name, value)


def update_properties(card_model: CardModel, values_json: str, on_error: FieldError) -> None:
    """按 JSON 对象一次写入多个字段；非对象或解析失败发字段错误。"""
    try:
        values = json.loads(values_json)
    except json.JSONDecodeError:
        on_error("properties", "输入格式无效")
        return
    if not isinstance(values, dict):
        on_error("properties", "输入格式无效")
        return
    card_model.update_properties(values)


def update_resistance(card_model: CardModel, resistance_name: str, value: float) -> None:
    """写入单项异常抗性。"""
    card_model.update_abnormal_resistance(resistance_name, value)


def update_rating_score(card_model: CardModel, index: int, score: int) -> None:
    """写入第 index 个评价维度的分数。"""
    card_model.update_rating_score(index, score)


def set_rating_radar_pref(
    card_model: CardModel,
    render: RenderCoordinator,
    enabled: bool,
    on_error: FieldError,
    on_changed: Callable[[bool], None],
) -> None:
    """写评价展示方式并触发重绘；写盘失败时回滚界面状态并发字段错误。"""
    if is_rating_radar() == bool(enabled):
        return
    try:
        set_rating_radar(bool(enabled))
    except FileOperationError as error:
        on_error("rating_display", str(error))
        on_changed(is_rating_radar())
        return
    on_changed(bool(enabled))
    render.request(card_model.enemy_data, current_render_options())


def apply_rating_schema(
    card_model: CardModel, draft_json: str, save_template: bool, on_error: FieldError
) -> bool:
    """把草稿套到当前卡的内存；`save_template` 为真时同时写入新建模板。不写卡片配置。

    返回是否成功；失败时发字段错误（草稿形状、模板校验或写盘失败）。
    """
    try:
        raw = json.loads(draft_json)
        if not isinstance(raw, list):
            raise ValueError("评价标准格式无效")
        draft_ids: list[str] = []
        names: list[str] = []
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError("评价标准格式无效")
            draft_ids.append(str(item.get("id", "")))
            names.append(str(item.get("name", "")).strip()[:8] or "未命名")
        schema = RatingSchema(names=names)
        scores = scores_for_rating_draft(
            [item.score for item in card_model.enemy_data.ratings],
            draft_ids,
        )
        next_enemy = card_model.enemy_with_ratings(list(schema.names), scores)
        if save_template:
            save_rating_schema(schema)
        card_model.apply_enemy_data(next_enemy)
    except (FileOperationError, TypeError, ValueError, json.JSONDecodeError) as error:
        on_error("rating_schema", str(error))
        return False
    return True


def choose_avatar(card_model: CardModel, parent: QWidget | None) -> None:
    """弹原生文件选择框；选中后写入 `avatar_path`，取消则不动。"""
    path, _ = QFileDialog.getOpenFileName(
        parent, "选择头像", "", "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
    )
    if path:
        card_model.update_property("avatar_path", path)
