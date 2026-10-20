"""PRTS 域：查询名规整、级别列表交付、级别切换的合法性判定。"""

from __future__ import annotations

import json


def query_name(raw: str) -> str | None:
    """查询用的敌人名；全空白返回 None（调用方据此忽略本次操作）。"""
    stripped = raw.strip()
    return stripped or None


def levels_json(levels: list[dict]) -> str:
    """级别列表（JSON 数组）；未导入或已换卡时为空数组。"""
    return json.dumps(levels, ensure_ascii=False)


def allows_level_change(levels: list[dict], level_index: int) -> bool:
    """没有导入上下文、或目标级别不在本次页面级别表内时不允许切换。"""
    if not levels:
        return False
    return any(item.get("index") == level_index for item in levels)
