"""合并后的原始字典 → EnemyData（Pydantic 组装 + 类型强转）。"""

from __future__ import annotations

import logging
from typing import Any, Optional

from models import EnemyData, SkillEntry, default_ratings
from utils.app.rating_prefs import get_rating_names

logger = logging.getLogger(__name__)


def to_enemy_data(raw: dict[str, Any], fallback_name: str) -> Optional[EnemyData]:
    """将管线合并字典转为 EnemyData（缺省字段用卡片编辑默认值）。"""
    if "error" in raw:
        return None
    ab = raw.get("abnormal_resistances")
    if not isinstance(ab, dict):
        ab = {}
    names = get_rating_names()
    try:
        return EnemyData(
            name=str(raw.get("name") or fallback_name),
            grade=str(raw.get("grade") or "C"),
            attack_type=str(raw.get("attack_type") or "近战"),
            damage_type=str(raw.get("damage_type") or "物理"),
            action_type=str(raw.get("action_type") or "地面"),
            hp_recovery_speed=float(raw.get("hp_recovery_speed") or 0),
            position=str(raw.get("position") or "普通"),
            category=str(raw.get("category") or "其他"),
            max_hp=int(raw.get("max_hp") or 1000),
            attack=int(raw.get("attack") or 100),
            defense=int(raw.get("defense") or 50),
            magic_resistance=int(raw.get("magic_resistance") or 10),
            attack_range_radius=float(raw.get("attack_range_radius") or 0),
            weight_level=int(raw.get("weight_level") or 1),
            move_speed=float(raw.get("move_speed") or 1.0),
            attack_interval=float(raw.get("attack_interval") or 2.0),
            damage_resistance=int(raw.get("damage_resistance") or 0),
            element_resistance=int(raw.get("element_resistance") or 0),
            base_taunt_level=int(raw.get("base_taunt_level") or 0),
            target_value=int(raw.get("target_value") or 1),
            brief_description=str(
                raw.get("brief_description") or f"来自PRTS的{fallback_name}数据"
            ),
            brief_comment=str(raw.get("brief_comment") or "待评价"),
            abnormal_resistances={k: float(v) for k, v in ab.items()},
            ratings=default_ratings(names),
            avatar_path=raw.get("avatar_path"),
            skills=_normalize_skills_payload(raw.get("skills")),
            talents_abilities=str(raw.get("talents_abilities") or ""),
        )
    except Exception as e:
        logger.error("EnemyData 构建失败: %s", e)
        return None


_PRESERVED_AUTHOR_FIELDS = ("brief_comment", "ratings", "grade", "avatar_path")


def rebuild_enemy_data(
    raw: dict[str, Any], fallback_name: str, current: EnemyData
) -> Optional[EnemyData]:
    """按新的合并字典重建敌人数据，保留当前卡上的作者字段（简评 / 评分 / 等级 / 头像）。

    切换 PRTS 级别只应改变 PRTS 来源的字段；``to_enemy_data`` 会把缺省字段回退成卡片默认值，
    直接套用会抹掉作者已填写的内容。
    """
    rebuilt = to_enemy_data(raw, fallback_name)
    if rebuilt is None:
        return None
    return rebuilt.model_copy(
        update={field: getattr(current, field) for field in _PRESERVED_AUTHOR_FIELDS}
    )


def _normalize_skills_payload(raw: Any) -> list[SkillEntry]:
    """保证 skills 为 list[SkillEntry]。"""
    if not isinstance(raw, list):
        return []
    out: list[SkillEntry] = []
    for item in raw:
        if isinstance(item, SkillEntry):
            out.append(item)
        elif isinstance(item, dict):
            out.append(
                SkillEntry(
                    名称=str(item.get("名称", "") or ""),
                    冷却时间=str(item.get("冷却时间", "") or ""),
                    技力消耗=str(item.get("技力消耗", "") or ""),
                    效果=str(item.get("效果", "") or ""),
                )
            )
    return out


def strip_debug_keys(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if not k.startswith("_")}
