"""敌人卡片编辑用的核心数据模型。"""

from typing import Any, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

from .media import is_url
from .rating_schema import DEFAULT_RATING_NAMES, MAX_RATING_DIMENSIONS, RatingEntry
from .skill_entry import SkillEntry


class EnemyData(BaseModel):

    name: str = Field(..., description="敌人名称")
    grade: str = Field(..., description="等级 (S/A/B/C/D)")

    attack_type: str = Field(..., description="攻击方式")
    damage_type: str = Field(..., description="伤害类型 (物理/法术)")
    action_type: str = Field(..., description="行动方式")
    hp_recovery_speed: float = Field(..., ge=0.0, description="生命自回速度")
    position: str = Field(..., description="地位")
    category: str = Field(..., description="种类")
    max_hp: int = Field(..., ge=0, description="最大生命值")
    attack: int = Field(..., ge=0, description="攻击力")
    defense: int = Field(..., ge=0, description="防御力")
    magic_resistance: int = Field(..., ge=0, description="法术抗性")
    attack_range_radius: float = Field(..., ge=0, description="攻击范围半径")
    weight_level: int = Field(..., ge=0, description="重量等级")
    move_speed: float = Field(..., ge=0, description="移动速度")
    attack_interval: float = Field(..., ge=0.0, description="攻击间隔")
    damage_resistance: int = Field(..., ge=0, description="损伤抗性")
    element_resistance: int = Field(..., ge=0, description="元素抗性")
    base_taunt_level: int = Field(..., ge=0, description="基础嘲讽等级")
    target_value: int = Field(..., ge=0, description="目标价值")

    brief_description: str = Field(..., description="简要描述")
    brief_comment: str = Field(..., description="简评内容")

    abnormal_resistances: dict[str, float] = Field(
        default_factory=dict, description="异常抗性映射"
    )

    ratings: list[RatingEntry] = Field(
        default_factory=list,
        max_length=MAX_RATING_DIMENSIONS,
        description="本卡评价，每项含名称与分数；顺序即从上到下",
    )

    avatar_path: Optional[str] = Field(
        None,
        description="头像图片路径：图片 URL，或本地路径（可为相对配置目录的相对路径）",
    )

    skills: list[SkillEntry] = Field(default_factory=list, description="技能列表")
    talents_abilities: str = Field(default="", description="天赋&能力描述文本")

    @model_validator(mode="before")
    @classmethod
    def coerce_legacy_ratings(cls, data: Any) -> Any:
        """没有 ratings 时，用成对的名称与分数，或仅有的默认三维分数组装。"""
        if not isinstance(data, dict) or "ratings" in data:
            return data
        scores = data.get("rating_scores", [])
        names = data.get("rating_names")
        if not isinstance(scores, list):
            return data
        if isinstance(names, list):
            if len(names) != len(scores):
                raise ValueError("评价维度与分数数量必须一致")
            entries = [{"name": name, "score": score} for name, score in zip(names, scores)]
        elif len(scores) == 0:
            entries = []
        elif len(scores) == len(DEFAULT_RATING_NAMES):
            entries = [
                {"name": name, "score": score}
                for name, score in zip(DEFAULT_RATING_NAMES, scores)
            ]
        else:
            raise ValueError(f"评分有 {len(scores)} 项但没有维度名称")
        copied = dict(data)
        copied["ratings"] = entries
        return copied

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, v):
        if v not in ["S", "A", "B", "C", "D"]:
            raise ValueError("等级必须是 S/A/B/C/D 中的一个")
        return v

    @field_validator("avatar_path")
    @classmethod
    def validate_avatar_path(cls, v):
        """只校验形状：URL 需可解析出主机；本地路径只要求非空。"""
        if not v:
            return v

        if is_url(v):
            parsed = urlparse(v)
            if not all([parsed.scheme, parsed.netloc]):
                raise ValueError(f"无效的图片URL: {v}")
        return v
