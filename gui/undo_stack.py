"""状态式撤销命令。

一条命令保存变更前后的两份 ``EnemyData``。模型替换与信号只发生在 ``redo`` / ``undo``。
``QUndoStack.push`` 会调用 ``redo``。``redo`` / ``undo`` 内不得再入栈。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QUndoCommand

from models import EnemyData

if TYPE_CHECKING:
    from gui.card_model import CardModel


class _StateCommand(QUndoCommand):
    """前后两份卡片快照。``refresh_snapshot`` 为真时恢复标量表单。"""

    def __init__(
        self,
        model: CardModel,
        previous: EnemyData,
        next_: EnemyData,
        refresh_snapshot: bool,
    ) -> None:
        super().__init__()
        self._model = model
        self._previous = previous.model_copy(deep=True)
        self._next = next_.model_copy(deep=True)
        self._refresh_snapshot = refresh_snapshot

    def undo(self) -> None:
        self._model.restore_state(self._previous, self._refresh_snapshot)

    def redo(self) -> None:
        self._model.restore_state(self._next, self._refresh_snapshot)
