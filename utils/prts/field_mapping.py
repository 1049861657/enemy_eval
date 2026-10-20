"""PRTS 字段名映射表与映射业务规则。

把 wikitext 模板解析出的中文字段键值对（utils/prts/wikitext_templates.py 的输出）
转换为 EnemyData 使用的英文字段字典，不涉及 HTTP/Pydantic。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from models import SkillEntry
from .wikitext_templates import (
    _extract_all_template_bodies,
    _extract_template_body,
    _parse_template_params,
)

logger = logging.getLogger(__name__)

LEVEL_TEMPLATE = "敌人信息/levelcontent"
COMMON_TEMPLATE = "敌人信息/common2"


@dataclass(frozen=True)
class EnemyLevel:
    """页面上的一个级别。index 为 levelcontent 的 index 参数；label 取自页面标题。"""

    index: int
    label: str

LEVEL_KEY_MAP: dict[str, str] = {
    "名称": "name",
    "地位": "position",
    "种类": "category",
    "描述": "brief_description",
    "攻击方式": "attack_type",
    "行动方式": "action_type",
    "最大生命值": "max_hp",
    "攻击力": "attack",
    "防御力": "defense",
    "法术抗性": "magic_resistance",
    "攻击范围半径": "attack_range_radius",
    "移动速度": "move_speed",
    "攻击间隔": "attack_interval",
    "生命恢复速度": "hp_recovery_speed",
    "重量等级": "weight_level",
    "损伤抵抗": "damage_resistance",
    "元素抗性": "element_resistance",
    "基础嘲讽等级": "base_taunt_level",
    "数量": "target_value",
    "天赋": "talents_abilities",
}

COMMON_KEY_MAP: dict[str, str] = {
    "名称": "name",
    "地位级别": "position",
    "描述": "brief_description_common",
    "伤害类型": "damage_type",
    "攻击方式": "attack_type",
    "行动方式": "action_type",
}

ABNORMAL_MAP: dict[str, str] = {
    "眩晕抗性": "晕眩",
    "沉默抗性": "沉默",
    "沉睡抗性": "沉睡",
    "冻结抗性": "冻结",
    "浮空抗性": "浮空",
    "战栗抗性": "战栗",
    "恐惧抗性": "恐惧",
    "麻痹抗性": "麻痹",
    "诱导抗性": "诱导",
}

_SKILL_FIELD_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^技能(\d+)$"), "名称"),
    (re.compile(r"^技能(\d+)初始$"), "初始"),
    (re.compile(r"^技能(\d+)消耗$"), "消耗"),
    (re.compile(r"^技能(\d+)效果$"), "效果"),
    (re.compile(r"^技能(\d+)技力消耗$"), "技力消耗"),
    (re.compile(r"^技能(\d+)技力$"), "技力消耗"),
]


def _clean_num_text(text: str) -> str:
    t = re.sub(r"\s+", "", (text or "").strip())
    if t in ("", "—", "-", "无"):
        return ""
    return t


def _to_float(text: str) -> float:
    s = _clean_num_text(text)
    if not s:
        return 0.0
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group(0)) if m else 0.0


def _to_int(text: str) -> int:
    return int(round(_to_float(text)))


def _strip_wiki_html_comments(text: str) -> str:
    """去掉 wikitext 里误带入的 <!-- ... -->（如 PRTS 模板内嵌 JSON 注释）。"""
    return re.sub(r"<!--[\s\S]*?-->", "", text)


def _skill_slots_from_level_zh(zh: dict[str, str]) -> dict[int, dict[str, str]]:
    """从单个 levelcontent 参数表抽取 技能0/技能0初始/… 等到按槽位索引的字典。"""
    slots: dict[int, dict[str, str]] = {}
    for k, v in zh.items():
        val = (v or "").strip()
        if not val:
            continue
        matched = False
        for rx, dest in _SKILL_FIELD_PATTERNS:
            m = rx.match(k)
            if m:
                idx = int(m.group(1))
                slots.setdefault(idx, {})[dest] = val
                matched = True
                break
        if not matched and re.match(r"^技能\d+.*$", k):
            logger.debug("字段 %r 形似技能字段但未匹配任何已知模式，已丢弃", k)
    return slots


def _merge_skill_slots(
    acc: dict[int, dict[str, str]], delta: dict[int, dict[str, str]]
) -> None:
    for idx, part in delta.items():
        acc.setdefault(idx, {})
        acc[idx].update(part)


def _skill_slots_to_card_skills(slots: dict[int, dict[str, str]]) -> list[SkillEntry]:
    """
    转为 EnemyData / GUI 使用的技能列表：
    名称、冷却时间（初动/回转）、技力消耗、效果。
    """
    out: list[SkillEntry] = []
    for i in sorted(slots.keys()):
        d = slots[i]
        name = _strip_wiki_html_comments((d.get("名称") or "").strip()).strip()
        effect = _strip_wiki_html_comments((d.get("效果") or "").strip()).strip()
        if not name and not effect:
            continue
        chu, hui = d.get("初始"), d.get("消耗")
        if chu is not None and hui is not None:
            cool = f"{chu}/{hui}"
        elif chu is not None:
            cool = str(chu)
        elif hui is not None:
            cool = str(hui)
        else:
            cool = ""
        sp = (d.get("技力消耗") or "").strip()
        out.append(
            SkillEntry(
                名称=name or f"技能{i}",
                冷却时间=cool,
                技力消耗=sp,
                效果=effect,
            )
        )
    return out


def _resistance_val(raw: str) -> float:
    s = (raw or "").strip()
    if not s or s == "无":
        return 0.0
    return 1.0


def _map_level_block(zh: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    abnormal: dict[str, float] = {}
    for zk, vv in zh.items():
        if zk in ABNORMAL_MAP:
            abnormal[ABNORMAL_MAP[zk]] = _resistance_val(vv)
            continue
        en = LEVEL_KEY_MAP.get(zk)
        if not en:
            continue
        if en in (
            "max_hp",
            "attack",
            "defense",
            "magic_resistance",
            "weight_level",
            "damage_resistance",
            "element_resistance",
            "base_taunt_level",
            "target_value",
        ):
            out[en] = _to_int(vv)
        elif en in ("move_speed", "attack_interval", "attack_range_radius", "hp_recovery_speed"):
            out[en] = _to_float(vv)
        elif en == "talents_abilities":
            out[en] = vv.strip()
        else:
            out[en] = vv.strip()
    if abnormal:
        out["abnormal_resistances"] = abnormal
    return out


def _map_common_block(zh: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for zk, vv in zh.items():
        en = COMMON_KEY_MAP.get(zk)
        if not en:
            continue
        out[en] = vv.strip()
    return out


def _level_blocks(wikitext: str) -> list[tuple[int, dict[str, str]]]:
    """按 index 升序返回各级别 levelcontent 的参数表；同 index 多块按出现顺序合并。"""
    blocks: dict[int, dict[str, str]] = {}
    for body in _extract_all_template_bodies(wikitext, LEVEL_TEMPLATE):
        p = _parse_template_params(body)
        raw_index = (p.get("index") or "0").strip() or "0"
        try:
            idx = int(raw_index)
        except ValueError:
            logger.warning(
                "levelcontent 的 index=%r 无法解析为整数，兜底为 0（可能导致多个 levelcontent 覆盖顺序错乱）",
                raw_index,
            )
            idx = 0
        blocks.setdefault(idx, {}).update(p)
    return sorted(blocks.items())


def _merge_levels(
    blocks: list[tuple[int, dict[str, str]]], max_index: int | None
) -> dict[str, Any]:
    """把级别块按 index 升序覆盖合并（每级只是上一级的增量）；max_index 给定时只覆盖到该级别。"""
    merged: dict[str, Any] = {}
    ab_acc: dict[str, float] = {}
    skill_slots: dict[int, dict[str, str]] = {}
    for idx, zh in blocks:
        if max_index is not None and idx > max_index:
            break
        _merge_skill_slots(skill_slots, _skill_slots_from_level_zh(zh))
        part = _map_level_block(zh)
        ab = part.pop("abnormal_resistances", None)
        if ab:
            ab_acc.update(ab)
        merged.update(part)
    if ab_acc:
        merged["abnormal_resistances"] = ab_acc
    merged["skills"] = [
        s.model_dump() for s in _skill_slots_to_card_skills(skill_slots)
    ]

    return merged


_LEVEL_HEADING = re.compile(r"^==\s*(级别\s*\d+)\s*==\s*$", re.MULTILINE)


def _level_labels(wikitext: str) -> dict[int, str]:
    """标题里的级别名（``==级别1==``）→ {index: 文本}；标题缺失时由调用方自造。"""
    labels: dict[int, str] = {}
    for text in _LEVEL_HEADING.findall(wikitext):
        digits = re.search(r"\d+", text)
        if digits:
            labels[int(digits.group(0))] = re.sub(r"\s+", "", text)
    return labels


def parse_enemy_levels(wikitext: str) -> list[EnemyLevel]:
    """列出页面上的级别（按 index 升序）；没有 levelcontent 时返回空表。"""
    blocks = _level_blocks(wikitext)
    labels = _level_labels(wikitext)
    return [
        EnemyLevel(index=idx, label=labels.get(idx, f"级别{idx}"))
        for idx, _ in blocks
    ]


def build_enemy_raw(wikitext: str, level_index: int | None = None) -> dict[str, Any] | None:
    """合并 common2 与 levelcontent。level_index 为 None 时覆盖到最高级别（导入默认）。"""
    common_body = _extract_template_body(wikitext, COMMON_TEMPLATE)
    blocks = _level_blocks(wikitext)
    if not common_body and not blocks:
        return None

    merged: dict[str, Any] = {}
    if common_body:
        merged.update(_map_common_block(_parse_template_params(common_body)))
    merged.update(_merge_levels(blocks, level_index))

    if merged.get("brief_description_common") and not merged.get("brief_description"):
        merged["brief_description"] = merged.pop("brief_description_common")
    elif merged.get("brief_description_common"):
        merged.pop("brief_description_common")

    merged.setdefault("talents_abilities", "")

    if isinstance(merged.get("brief_description"), str):
        merged["brief_description"] = _strip_wiki_html_comments(
            merged["brief_description"]
        ).strip()
    if isinstance(merged.get("talents_abilities"), str):
        merged["talents_abilities"] = _strip_wiki_html_comments(
            merged["talents_abilities"]
        ).strip()

    cat = merged.get("category", "")
    if isinstance(cat, str) and not cat.strip():
        merged["category"] = "其他"

    return merged if merged else None
