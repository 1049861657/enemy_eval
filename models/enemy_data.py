"""敌人卡片编辑用的核心数据模型。"""

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from .media import is_url
from .rating_schema import MAX_RATING_DIMENSIONS
from .skill_entry import SkillEntry


class EnemyData(BaseModel):
    """敌人数据模型"""

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

    rating_scores: list[int] = Field(
        default_factory=list,
        max_length=MAX_RATING_DIMENSIONS,
        description="各评价维度分数(1-5)，与全局评价标准顺序对应；名称不在此持久化",
    )

    avatar_path: Optional[str] = Field(None, description="头像图片路径")

    skills: list[SkillEntry] = Field(default_factory=list, description="技能列表")
    talents_abilities: str = Field(default="", description="天赋&能力描述文本")

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, v):
        if v not in ["S", "A", "B", "C", "D"]:
            raise ValueError("等级必须是 S/A/B/C/D 中的一个")
        return v

    @field_validator("rating_scores")
    @classmethod
    def validate_rating_scores(cls, v: list[int]) -> list[int]:
        if len(v) > MAX_RATING_DIMENSIONS:
            raise ValueError(f"评分项最多 {MAX_RATING_DIMENSIONS} 个")
        for score in v:
            if not isinstance(score, int) or isinstance(score, bool):
                raise ValueError("评分必须是整数")
            if score < 1 or score > 5:
                raise ValueError("评分必须在 1-5 之间")
        return v

    @field_validator("avatar_path")
    @classmethod
    def validate_avatar_path(cls, v):
        if not v:
            return v

        if is_url(v):
            parsed = urlparse(v)
            if not all([parsed.scheme, parsed.netloc]):
                raise ValueError(f"无效的图片URL: {v}")
        else:
            if not Path(v).exists():
                raise ValueError(f"图片文件不存在: {v}")
        return v
