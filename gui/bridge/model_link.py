"""把 CardModel / 撤销栈的信号接到桥接层：快照、字段错误、级别来源、撤销态。

订阅与退订必须成对（换卡时先退旧的再订新的），否则 QML 会收到过期模型的通知。
回调由桥接层传入，本模块不声明 Qt 元对象。
"""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from gui.card_model import CardModel

ModelChanged = Callable[[], None]
FieldError = Callable[[str, str], None]
LevelChanged = Callable[[int], None]
UndoStateChanged = Callable[[bool], None]


class CardModelLink:
    """`CardModel` 的订阅者：`attach` 一份新模型时自动退掉上一份。"""

    def __init__(
        self,
        on_model_changed: ModelChanged,
        on_field_error: FieldError,
        on_level_changed: LevelChanged,
        on_undo_state: UndoStateChanged,
    ) -> None:
        self._on_model_changed = on_model_changed
        self._on_field_error = on_field_error
        self._on_level_changed = on_level_changed
        self._on_undo_state = on_undo_state
        self._card_model: CardModel | None = None

    def attach(self, card_model: CardModel) -> None:
        """订阅新模型的四类变化；已有订阅先退掉。"""
        self.detach()
        self._card_model = card_model
        card_model.snapshotChanged.connect(self._on_model_changed)
        card_model.validationFailed.connect(self._on_field_error)
        card_model.prtsLevelChanged.connect(self._on_level_changed)
        stack = card_model.undo_stack()
        stack.canUndoChanged.connect(self._on_undo_state)
        stack.canRedoChanged.connect(self._on_undo_state)

    def detach(self) -> None:
        """退订当前模型；未订阅时静默返回（重复退订不报错）。"""
        card_model = self._card_model
        if card_model is None:
            return
        stack = card_model.undo_stack()
        for signal, slot in (
            (card_model.snapshotChanged, self._on_model_changed),
            (card_model.validationFailed, self._on_field_error),
            (card_model.prtsLevelChanged, self._on_level_changed),
            (stack.canUndoChanged, self._on_undo_state),
            (stack.canRedoChanged, self._on_undo_state),
        ):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass
        self._card_model = None
