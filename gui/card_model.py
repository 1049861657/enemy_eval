"""
卡片数据模型 - 支持实时更新的GUI数据模型
"""

import json
import logging
from typing import Dict, Any

from PySide6.QtCore import QObject, Signal

from models import EnemyData, SkillEntry
from utils.error_handler import FileOperationError

logger = logging.getLogger(__name__)


class CardModel(QObject):
    """支持信号机制的卡片数据模型"""

    # 信号定义
    dataChanged = Signal()  # 当任何数据发生变化时发出
    cardGenerated = Signal(str)  # 当卡片生成完成时发出，传递图片路径
    validationFailed = Signal(str, str)  # (property_name, error_message)：属性校验失败时发出，供 UI 恢复为模型当前真实值
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._enemy_data = self._create_default_enemy_data()
        
    def _create_default_enemy_data(self) -> EnemyData:
        """创建默认的敌人数据"""
        return EnemyData(
            name="新敌人",
            attack_type="近战",
            damage_type="物理",
            action_type="地面",
            hp_recovery_speed=0.0,
            position="普通",
            category="其他",
            max_hp=1000,
            attack=100,
            defense=50,
            magic_resistance=10,
            attack_range_radius=0.0,
            weight_level=1,
            move_speed=1.0,
            attack_interval=2.0,
            damage_resistance=0,
            element_resistance=0,
            base_taunt_level=0,
            target_value=1,
            brief_description="这是一个新的敌人，请填写描述",
            brief_comment="待评价",
            abnormal_resistances={},
            hostility_rating=3,
            innovation_rating=3,
            threat_rating=3,
            grade="C",
            avatar_path="",
            skills=[],
            talents_abilities=""
        )
    
    @property
    def enemy_data(self) -> EnemyData:
        """获取敌人数据"""
        return self._enemy_data
    
    def update_property(self, property_name: str, value: Any):
        """更新属性值并发出信号"""
        if hasattr(self._enemy_data, property_name):
            # 使用pydantic的方式更新属性
            current_dict = self._enemy_data.model_dump()
            current_dict[property_name] = value
            
            try:
                # 验证数据
                self._enemy_data = EnemyData(**current_dict)
                self.dataChanged.emit()
            except Exception as e:
                logger.error("属性 %s 校验失败: %s", property_name, e, exc_info=True)
                self.validationFailed.emit(property_name, str(e))
    
    def update_skill(self, index: int, skill_data: Dict[str, str] | SkillEntry):
        """更新技能数据"""
        entry = (
            skill_data
            if isinstance(skill_data, SkillEntry)
            else SkillEntry.model_validate(skill_data)
        )
        skills = list(self._enemy_data.skills)
        while len(skills) <= index:
            skills.append(SkillEntry())
        skills[index] = entry
        skills = [s for s in skills if s.is_nonempty()]
        self.update_property("skills", skills)
    
    def update_abnormal_resistance(self, resistance_name: str, value: float):
        """更新异常抗性"""
        resistances: Dict[str, float] = dict(self._enemy_data.abnormal_resistances)
        resistances[resistance_name] = value
        self.update_property('abnormal_resistances', resistances)
    
    def load_from_file(self, file_path: str) -> None:
        """从文件加载数据；失败时抛出 FileOperationError，不吞异常。"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._enemy_data = EnemyData(**data)
        except Exception as e:
            logger.error("加载文件失败: %s", e, exc_info=True)
            raise FileOperationError(f"加载文件失败: {e}") from e
        self.dataChanged.emit()
    
    def save_to_file(self, file_path: str) -> None:
        """保存数据到文件；失败时抛出 FileOperationError，不吞异常。"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._enemy_data.model_dump(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("保存文件失败: %s", e, exc_info=True)
            raise FileOperationError(f"保存文件失败: {e}") from e
    
    def set_enemy_data(self, enemy_data: EnemyData):
        """设置完整的敌人数据"""
        self._enemy_data = enemy_data
        self.dataChanged.emit()
    
    def get_current_dict(self) -> Dict[str, Any]:
        """获取当前数据的字典形式"""
        return self._enemy_data.model_dump()