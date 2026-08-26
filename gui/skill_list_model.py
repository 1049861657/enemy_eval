"""技能列表的 Qt 模型；QML Repeater 绑定角色，增删改走本模型的 slot。"""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    Qt,
    Signal,
    Slot,
)

from models import SkillEntry

from .card_model import CardModel

_FIELD_BY_ROLE: dict[int, str] = {
    Qt.ItemDataRole.UserRole + 1: "名称",
    Qt.ItemDataRole.UserRole + 2: "冷却时间",
    Qt.ItemDataRole.UserRole + 3: "技力消耗",
    Qt.ItemDataRole.UserRole + 4: "效果",
}


class SkillListModel(QAbstractListModel):
    """以 CardModel.enemy_data.skills 为源，不把整表技能 JSON 丢给 QML。"""

    NameRole = Qt.ItemDataRole.UserRole + 1
    CooldownRole = Qt.ItemDataRole.UserRole + 2
    CostRole = Qt.ItemDataRole.UserRole + 3
    EffectRole = Qt.ItemDataRole.UserRole + 4

    countChanged = Signal()

    def __init__(self, card_model: CardModel, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._card_model = card_model
        self._mutating = False
        self._card_model.dataChanged.connect(self._on_card_changed)

    def set_card_model(self, card_model: CardModel) -> None:
        if self._card_model is card_model:
            return
        try:
            self._card_model.dataChanged.disconnect(self._on_card_changed)
        except (RuntimeError, TypeError):
            pass
        self._card_model = card_model
        self._card_model.dataChanged.connect(self._on_card_changed)
        self.beginResetModel()
        self.endResetModel()
        self.countChanged.emit()

    def _on_card_changed(self) -> None:
        if self._mutating:
            return
        self.beginResetModel()
        self.endResetModel()
        self.countChanged.emit()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._card_model.enemy_data.skills)

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802
        return {
            self.NameRole: QByteArray(b"skillName"),
            self.CooldownRole: QByteArray(b"cooldown"),
            self.CostRole: QByteArray(b"cost"),
            self.EffectRole: QByteArray(b"effect"),
        }

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        skills = self._card_model.enemy_data.skills
        row = index.row()
        if row < 0 or row >= len(skills):
            return None
        field = _FIELD_BY_ROLE.get(role)
        if field is None:
            return None
        return getattr(skills[row], field)

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return self.rowCount()

    def _commit(self, skills: list[SkillEntry]) -> bool:
        return self._card_model.replace_skills(skills)

    @Slot()
    def add(self) -> None:
        skills = list(self._card_model.enemy_data.skills)
        row = len(skills)
        skills.append(SkillEntry())
        self.beginInsertRows(QModelIndex(), row, row)
        self._mutating = True
        try:
            ok = self._commit(skills)
        finally:
            self._mutating = False
        self.endInsertRows()
        if ok:
            self.countChanged.emit()

    @Slot(int)
    def remove(self, index: int) -> None:
        skills = list(self._card_model.enemy_data.skills)
        if index < 0 or index >= len(skills):
            return
        self.beginRemoveRows(QModelIndex(), index, index)
        del skills[index]
        self._mutating = True
        try:
            ok = self._commit(skills)
        finally:
            self._mutating = False
        self.endRemoveRows()
        if ok:
            self.countChanged.emit()

    @Slot(int, str, str)
    def updateField(self, index: int, field: str, value: str) -> None:  # noqa: N802
        skills = list(self._card_model.enemy_data.skills)
        if index < 0 or index >= len(skills):
            return
        if field not in _FIELD_BY_ROLE.values():
            return
        skills[index] = skills[index].model_copy(update={field: value})
        self._mutating = True
        try:
            if not self._commit(skills):
                return
        finally:
            self._mutating = False
        role = next(role_id for role_id, name in _FIELD_BY_ROLE.items() if name == field)
        model_index = self.index(index, 0)
        self.dataChanged.emit(model_index, model_index, [role])
