"""状态式撤销命令。

一条命令保存变更前后的两份 ``_CardSnapshot``（敌人数据 + 该数据取自 PRTS 的哪一级别）。
模型替换与信号只发生在 ``redo`` / ``undo``。``QUndoStack.push`` 会调用 ``redo``。
``redo`` / ``undo`` 内不得再入栈。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtGui import QUndoCommand

from models import EnemyData

if TYPE_CHECKING:
    from gui.card_model import CardModel


@dataclass(frozen=True)
class _CardSnapshot:
    """一份卡片状态：数据，以及它的 PRTS 级别来源（取值语义见 ``CardModel.prts_level_index``）。"""

    enemy: EnemyData
    prts_level_index: int


class _StateCommand(QUndoCommand):
    """前后两份卡片状态。``refresh_snapshot`` 为真时恢复标量表单。"""

    def __init__(
        self,
        model: CardModel,
        previous: _CardSnapshot,
        next_: _CardSnapshot,
        refresh_snapshot: bool,
    ) -> None:
        super().__init__()
        self._model = model
        self._previous = _CardSnapshot(
            previous.enemy.model_copy(deep=True), previous.prts_level_index
        )
        self._next = _CardSnapshot(next_.enemy.model_copy(deep=True), next_.prts_level_index)
        self._refresh_snapshot = refresh_snapshot

    def undo(self) -> None:
        self._model.restore_state(self._previous, self._refresh_snapshot)

    def redo(self) -> None:
        self._model.restore_state(self._next, self._refresh_snapshot)
