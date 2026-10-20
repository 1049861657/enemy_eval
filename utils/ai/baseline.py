"""AI 评价基准：杰斯顿·威廉姆斯的级别0 数据，只读。core 不得导入本模块。"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..errors import FileOperationError
from ..app.resources import resource_manager

_BASELINE_RELATIVE_PATH = "resource/baseline/jesselton_config.json"

_REQUIRED_KEYS = (
    "name",
    "position",
    "category",
    "attack_type",
    "damage_type",
    "action_type",
    "max_hp",
    "attack",
    "defense",
    "magic_resistance",
    "attack_range_radius",
    "attack_interval",
    "move_speed",
    "hp_recovery_speed",
    "weight_level",
    "damage_resistance",
    "element_resistance",
    "base_taunt_level",
    "target_value",
    "brief_description",
    "talents_abilities",
    "skills",
)


@lru_cache(maxsize=1)
def _read_baseline() -> dict[str, Any]:
    path = Path(resource_manager.get_resource_path(_BASELINE_RELATIVE_PATH))
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FileOperationError(f"无法读取 AI 评价基准: {error}") from error
    if not isinstance(raw, dict):
        raise FileOperationError("AI 评价基准内容不是 JSON 对象")
    missing = [key for key in _REQUIRED_KEYS if key not in raw]
    if missing:
        raise FileOperationError(f"AI 评价基准缺少字段: {', '.join(missing)}")
    return raw


def load_baseline() -> dict[str, Any]:
    """基准数据（取自 PRTS 杰斯顿·威廉姆斯页级别0）；返回副本，调用方不得写回文件。"""
    return copy.deepcopy(_read_baseline())
