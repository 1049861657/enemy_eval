"""
卡片数据模型 - 支持实时更新的GUI数据模型
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack

from models import EnemyData, SkillEntry, default_ratings
from utils.app_settings_store import get_rating_names
from utils.fs.avatar_paths import resolve_stored_path, to_stored_path
from utils.errors import FileOperationError

from .undo_stack import _CardSnapshot, _StateCommand

logger = logging.getLogger(__name__)

# 当前卡数据没有 PRTS 级别来源：没从 PRTS 导入过，或导入后已换卡。
NO_PRTS_LEVEL = -1


class CardModel(QObject):
    """支持信号机制的卡片数据模型"""

    # 信号定义
    dataChanged = Signal()  # 当任何数据发生变化时发出
    snapshotChanged = Signal()  # 标量表单快照（不含技能列表）需要刷新
    validationFailed = Signal(str, str)  # (property_name, error_message)：属性校验失败时发出，供 UI 恢复为模型当前真实值
    avatarPathChanged = Signal(str)  # 头像路径变更（可能是网络 URL），GUI 据此补预缓存
    prtsLevelChanged = Signal(int)  # PRTS 级别来源变更（导入、切换级别、撤销回放）
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._enemy_data = self._create_default_enemy_data()
        self._prts_level_index: int = NO_PRTS_LEVEL
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(100)

    def undo_stack(self) -> QUndoStack:
        """当前卡片的撤销栈。换模型时由桥接重连其 canUndo/canRedo 信号。"""
        return self._undo_stack
        
    def _create_default_enemy_data(self) -> EnemyData:
        """创建默认的敌人数据。评价维度取当前新建模板。"""
        names = get_rating_names()
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
            ratings=default_ratings(names),
            grade="C",
            avatar_path="",
            skills=[],
            talents_abilities=""
        )
    
    @property
    def enemy_data(self) -> EnemyData:
        """获取敌人数据"""
        return self._enemy_data

    @property
    def prts_level_index(self) -> int:
        """当前卡数据取自 PRTS 的哪一级别；``NO_PRTS_LEVEL`` 表示无来源。随撤销栈快照回放。"""
        return self._prts_level_index

    def set_prts_level_index(self, level_index: int = NO_PRTS_LEVEL) -> None:
        """记录当前卡数据取自 PRTS 的哪一级别；不进撤销栈（导入路径调用，撤销栈随即清空）。"""
        self._apply_prts_level(level_index)

    def _apply_prts_level(self, level_index: int) -> None:
        if self._prts_level_index == level_index:
            return
        self._prts_level_index = level_index
        self.prtsLevelChanged.emit(level_index)
    
    def update_property(self, property_name: str, value: Any) -> None:
        """更新一个字段。校验通过后入栈一步。"""
        if hasattr(self._enemy_data, property_name):
            self.update_properties({property_name: value})

    def update_properties(self, values: dict[str, Any]) -> None:
        """一次写入多个字段。校验通过后只入栈一步。"""
        if not values:
            return
        if any(not hasattr(self._enemy_data, name) for name in values):
            return
        current = self._enemy_data.model_dump()
        current.update(values)
        try:
            next_data = EnemyData(**current)
        except Exception as error:
            field = next(iter(values))
            logger.error("属性 %s 校验失败: %s", field, error, exc_info=True)
            self.validationFailed.emit(field, str(error))
            return
        self._commit(self._snapshot(), _CardSnapshot(next_data, self._prts_level_index), True)
    
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
            next_data = EnemyData(**current_dict)
        except Exception as error:
            logger.error("技能列表校验失败: %s", error, exc_info=True)
            self.validationFailed.emit("skills", str(error))
            return False
        self._commit(self._snapshot(), _CardSnapshot(next_data, self._prts_level_index), False)
        return True
    
    def update_abnormal_resistance(self, resistance_name: str, value: float):
        """更新异常抗性"""
        resistances: Dict[str, float] = dict(self._enemy_data.abnormal_resistances)
        resistances[resistance_name] = value
        self.update_property('abnormal_resistances', resistances)

    def update_rating_score(self, index: int, score: int) -> None:
        """更新当前卡上单个维度的分数。"""
        ratings = [item.model_dump() for item in self._enemy_data.ratings]
        if index < 0 or index >= len(ratings):
            return
        ratings[index]["score"] = score
        self.update_property("ratings", ratings)

    def enemy_with_ratings(self, names: list[str], scores: list[int]) -> EnemyData:
        """返回套上这组维度和分数后的敌人数据，不改当前卡。"""
        payload = self._enemy_data.model_dump()
        payload["ratings"] = [
            {"name": name, "score": score} for name, score in zip(names, scores)
        ]
        return EnemyData(**payload)

    def apply_enemy_data(self, enemy: EnemyData, level_index: int | None = None) -> None:
        """把整份敌人数据写入当前卡并记入撤销。

        ``level_index`` 是这份数据的 PRTS 级别来源；省略（``None``）表示沿用当前来源，
        用于改动作者字段后的整份替换（如评价标准）。与当前状态完全相同则不动。不写配置文件。
        """
        if level_index is None:
            level_index = self._prts_level_index
        if enemy == self._enemy_data and level_index == self._prts_level_index:
            return
        self._commit(self._snapshot(), _CardSnapshot(enemy, level_index), True)
    
    def load_from_file(self, file_path: str) -> None:
        """从文件加载数据；相对头像路径按配置文件所在目录解析。失败时抛出 FileOperationError，不吞异常。"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            enemy = EnemyData(**data)
            resolved_avatar = resolve_stored_path(enemy.avatar_path or "", Path(file_path).parent)
            if resolved_avatar != (enemy.avatar_path or ""):
                enemy = enemy.model_copy(update={"avatar_path": resolved_avatar})
            self._enemy_data = enemy
            self._apply_prts_level(NO_PRTS_LEVEL)
        except Exception as e:
            logger.error("加载文件失败: %s", e, exc_info=True)
            raise FileOperationError(f"加载文件失败: {e}") from e
        self.dataChanged.emit()
        self.snapshotChanged.emit()
        self.avatarPathChanged.emit(self._enemy_data.avatar_path or "")
        self._undo_stack.clear()
    
    def save_to_file(self, file_path: str) -> None:
        """保存数据到文件；头像路径按目标文件所在目录转为存储形式。失败时抛出 FileOperationError，不吞异常。"""
        try:
            payload = self._enemy_data.model_dump()
            avatar_path = self._enemy_data.avatar_path
            if avatar_path:
                payload["avatar_path"] = to_stored_path(avatar_path, Path(file_path).parent)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("保存文件失败: %s", e, exc_info=True)
            raise FileOperationError(f"保存文件失败: {e}") from e
    
    def set_enemy_data(self, enemy_data: EnemyData):
        """设置完整的敌人数据。评价维度以这份数据自带的名称为准。级别来源由调用方随后打标。"""
        self._enemy_data = enemy_data
        self._apply_prts_level(NO_PRTS_LEVEL)
        self.dataChanged.emit()
        self.snapshotChanged.emit()
        self.avatarPathChanged.emit(self._enemy_data.avatar_path or "")
        self._undo_stack.clear()

    def restore_state(self, snapshot: _CardSnapshot, refresh_snapshot: bool) -> None:
        """装回一份快照（数据 + PRTS 级别来源）并发信号。由撤销命令的 redo/undo 调用，不入栈。"""
        previous_avatar = self._enemy_data.avatar_path or ""
        self._enemy_data = snapshot.enemy
        self._apply_prts_level(snapshot.prts_level_index)
        self.dataChanged.emit()
        if refresh_snapshot:
            self.snapshotChanged.emit()
        if (snapshot.enemy.avatar_path or "") != previous_avatar:
            self.avatarPathChanged.emit(snapshot.enemy.avatar_path or "")

    def _snapshot(self) -> _CardSnapshot:
        """当前卡片状态：数据 + PRTS 级别来源。"""
        return _CardSnapshot(self._enemy_data, self._prts_level_index)

    def _commit(self, previous: _CardSnapshot, next_: _CardSnapshot, refresh_snapshot: bool) -> None:
        """入栈。push 调用 redo，由 redo 写模型。"""
        self._undo_stack.push(_StateCommand(self, previous, next_, refresh_snapshot))
    
    def get_current_dict(self) -> Dict[str, Any]:
        """获取当前数据的字典形式"""
        return self._enemy_data.model_dump()