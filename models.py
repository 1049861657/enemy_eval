"""
数据模型定义 - 使用Pydantic V2进行现代化数据验证
"""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class EnemyData(BaseModel):
    """敌人数据模型"""
    
    # 基础信息
    name: str = Field(..., description="敌人名称")
    grade: str = Field(..., description="等级 (S/A/B/C/D)")
    
    # 主属性
    attack_type: str = Field(..., description="攻击方式")
    action_type: str = Field(..., description="行动方式") 
    hp_recovery_speed: float = Field(..., ge=0.0, description="生命恢复速度")
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
    
    # 简要描述
    brief_description: str = Field(..., description="简要描述")
    
    # 简评内容
    brief_comment: str = Field(..., description="简评内容")
    
    # 异常抗性字典 (只包含有抗性的属性)
    abnormal_resistances: dict[str, float] = Field(default_factory=dict, description="异常抗性映射")
    
    # 评价星级 (1-5星)
    hostility_rating: int = Field(..., ge=1, le=5, description="对策度")
    innovation_rating: int = Field(..., ge=1, le=5, description="创新度")
    threat_rating: int = Field(..., ge=1, le=5, description="威胁度")
    
    # 图片路径
    avatar_path: Optional[str] = Field(None, description="头像图片路径")
    
    # 技能与天赋&能力
    skills: list[dict[str, str]] = Field(default_factory=list, description="技能列表，每个技能包含名称、冷却时间、消耗等信息")
    talents_abilities: str = Field(default="", description="天赋&能力描述文本")
    
    @field_validator('grade')
    @classmethod
    def validate_grade(cls, v):
        """验证等级"""
        if v not in ['S', 'A', 'B', 'C', 'D']:
            raise ValueError('等级必须是 S/A/B/C/D 中的一个')
        return v
    
    @field_validator('avatar_path')
    @classmethod
    def validate_avatar_path(cls, v):
        """验证头像路径"""
        if v and not Path(v).exists():
            raise ValueError(f'图片文件不存在: {v}')
        return v

class CardStyle(BaseModel):
    """卡片样式配置"""
    
    # 画布尺寸
    width: int = Field(default=800, description="画布宽度")
    height: int = Field(default=600, description="画布高度")
    
    # 颜色配置
    background_color: str = Field(default="#f0f0f0", description="背景色")
    primary_color: str = Field(default="#333333", description="主要文字颜色")
    accent_color: str = Field(default="#ff6b6b", description="强调色")
    
    # 字体配置
    font_size_title: int = Field(default=24, description="标题字体大小")
    font_size_normal: int = Field(default=16, description="正常字体大小")
    font_size_small: int = Field(default=12, description="小字体大小")
    
    # 布局配置
    padding: int = Field(default=20, description="边距")
    avatar_size: int = Field(default=120, description="头像尺寸")
    star_size: int = Field(default=20, description="星星尺寸")