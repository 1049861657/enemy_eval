"""
卡片数据模型 - 支持实时更新的GUI数据模型
"""

import json
import logging
from typing import Dict, Any

from PySide6.QtCore import QObject, Signal

from models import EnemyData, SkillEntry, align_rating_scores
from utils.app_settings_store import default_scores_for_current_schema, get_rating_names
from utils.error_handler import FileOperationError

logger = logging.getLogger(__name__)


class CardModel(QObject):
    """支持信号机制的卡片数据模型"""

    # 信号定义
    dataChanged = Signal()  # 当任何数据发生变化时发出
    snapshotChanged = Signal()  # 标量表单快照（不含技能列表）需要刷新
    validationFailed = Signal(str, str)  # (property_name, error_message)：属性校验失败时发出，供 UI 恢复为模型当前真实值
    ratingSchemaChanged = Signal()  # 全局评价标准变更（名称/数量）
    avatarPathChanged = Signal(str)  # 头像路径变更（可能是网络 URL），GUI 据此补预缓存
    
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
            rating_scores=default_scores_for_current_schema(),
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
                self.snapshotChanged.emit()
                if property_name == "avatar_path":
                    self.avatarPathChanged.emit(self._enemy_data.avatar_path or "")
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
        self.replace_skills(skills)

    def replace_skills(self, skills: list[SkillEntry]) -> bool:
        """替换技能列表；成功后只发 dataChanged，不刷新标量 JSON 快照。"""
        current_dict = self._enemy_data.model_dump()
        current_dict["skills"] = [skill.model_dump() for skill in skills]
        try:
            self._enemy_data = EnemyData(**current_dict)
        except Exception as error:
            logger.error("技能列表校验失败: %s", error, exc_info=True)
            self.validationFailed.emit("skills", str(error))
            return False
        self.dataChanged.emit()
        return True
    
    def update_abnormal_resistance(self, resistance_name: str, value: float):
        """更新异常抗性"""
        resistances: Dict[str, float] = dict(self._enemy_data.abnormal_resistances)
        resistances[resistance_name] = value
        self.update_property('abnormal_resistances', resistances)

    def update_rating_score(self, index: int, score: int) -> None:
        """更新单个评价维度分数。"""
        names = get_rating_names()
        scores = align_rating_scores(list(self._enemy_data.rating_scores), len(names))
        if index < 0 or index >= len(scores):
            return
        scores[index] = score
        self.update_property("rating_scores", scores)

    def realign_rating_scores_to_schema(self) -> None:
        """按当前全局评价标准对齐分数长度（增维补默认分、减维截断）。"""
        names = get_rating_names()
        aligned = align_rating_scores(list(self._enemy_data.rating_scores), len(names))
        if aligned != list(self._enemy_data.rating_scores):
            current_dict = self._enemy_data.model_dump()
            current_dict["rating_scores"] = aligned
            self._enemy_data = EnemyData(**current_dict)
        self.ratingSchemaChanged.emit()
        self.dataChanged.emit()
        self.snapshotChanged.emit()
    
    def load_from_file(self, file_path: str) -> None:
        """从文件加载数据；失败时抛出 FileOperationError，不吞异常。"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            enemy = EnemyData(**data)
            names = get_rating_names()
            scores = align_rating_scores(list(enemy.rating_scores), len(names))
            if scores != list(enemy.rating_scores):
                enemy = enemy.model_copy(update={"rating_scores": scores})
            self._enemy_data = enemy
        except Exception as e:
            logger.error("加载文件失败: %s", e, exc_info=True)
            raise FileOperationError(f"加载文件失败: {e}") from e
        self.dataChanged.emit()
        self.snapshotChanged.emit()
        self.avatarPathChanged.emit(self._enemy_data.avatar_path or "")
    
    def save_to_file(self, file_path: str) -> None:
        """保存数据到文件；失败时抛出 FileOperationError，不吞异常。"""
        try:
            names = get_rating_names()
            payload = self._enemy_data.model_dump()
            payload["rating_scores"] = align_rating_scores(
                list(self._enemy_data.rating_scores), len(names)
            )
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("保存文件失败: %s", e, exc_info=True)
            raise FileOperationError(f"保存文件失败: {e}") from e
    
    def set_enemy_data(self, enemy_data: EnemyData):
        """设置完整的敌人数据；分数按当前评价标准对齐，保证与渲染侧等长。"""
        names = get_rating_names()
        scores = align_rating_scores(list(enemy_data.rating_scores), len(names))
        if scores != list(enemy_data.rating_scores):
            enemy_data = enemy_data.model_copy(update={"rating_scores": scores})
        self._enemy_data = enemy_data
        self.dataChanged.emit()
        self.snapshotChanged.emit()
        self.avatarPathChanged.emit(self._enemy_data.avatar_path or "")
    
    def get_current_dict(self) -> Dict[str, Any]:
        """获取当前数据的字典形式"""
        return self._enemy_data.model_dump()