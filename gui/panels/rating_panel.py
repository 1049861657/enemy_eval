"""
评价面板 - 处理敌人的评级和简评编辑

评价标准（名称/数量）保存为应用级用户设置；
分数按敌人持久化在各自 *_config.json 的 rating_scores。
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QFrame,
    QScrollArea,
    QPushButton,
    QLineEdit,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt, QPoint, QEvent
from PySide6.QtGui import QPainter, QColor, QPen, QPolygon

from models import (
    MAX_RATING_DIMENSIONS,
    RatingSchema,
    align_rating_scores,
    default_rating_scores,
)
from utils import FixedDebouncer
from utils.rating_schema_store import get_rating_names, load_rating_schema, save_rating_schema

from ..card_model import CardModel
from ..detailed_editor_dialog import DetailedEditorDialog
from ..styles import (
    STAR_RATING_STYLE,
    RATING_GROUP_STYLE,
    DESCRIPTION_GROUP_STYLE,
    COMMENT_GROUP_STYLE,
    DESCRIPTION_TITLE_STYLE,
    COMMENT_TITLE_STYLE,
    CONTENT_AREA_STYLE,
    RATING_LABEL_STYLE,
    DETAILED_TEXT_EDIT_STYLE,
    RATING_SETTINGS_BTN_STYLE,
    RATING_ADD_BTN_STYLE,
    RATING_REMOVE_BTN_STYLE,
    RATING_NAME_EDIT_STYLE,
    RATING_DONE_BTN_STYLE,
)


class StarRatingWidget(QWidget):
    """星级评价组件"""

    valueChanged = Signal(int)

    def __init__(self, max_stars: int = 5, current_value: int = 3):
        super().__init__()
        self.max_stars = max_stars
        self.current_value = current_value
        self.hover_value = 0
        self._interactive = True

        self.setFixedSize(140, 30)
        self.setMouseTracking(True)
        self.setStyleSheet(STAR_RATING_STYLE)

    def setInteractive(self, enabled: bool) -> None:
        self._interactive = enabled
        self.setEnabled(enabled)
        if not enabled:
            self.hover_value = 0
            self.update()

    def setValue(self, value: int, *, emit: bool = True) -> None:
        if 1 <= value <= self.max_stars:
            self.current_value = value
            self.update()
            if emit:
                self.valueChanged.emit(value)

    def getValue(self) -> int:
        return self.current_value

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        star_size = 20
        spacing = 4
        start_x = (self.width() - (self.max_stars * star_size + (self.max_stars - 1) * spacing)) // 2
        start_y = (self.height() - star_size) // 2

        for i in range(self.max_stars):
            x = start_x + i * (star_size + spacing)
            y = start_y
            display_value = self.hover_value if self.hover_value > 0 else self.current_value
            if i < display_value:
                painter.setBrush(QColor(255, 215, 0))
                painter.setPen(QPen(QColor(255, 193, 7), 1))
            else:
                painter.setBrush(QColor(220, 220, 220))
                painter.setPen(QPen(QColor(180, 180, 180), 1))
            self._draw_star(painter, x + star_size // 2, y + star_size // 2, star_size // 3)

    def _draw_star(self, painter, center_x, center_y, radius):
        points = []
        for i in range(10):
            angle = i * math.pi / 5
            r = radius if i % 2 == 0 else radius * 0.4
            x = center_x + r * math.cos(angle - math.pi / 2)
            y = center_y + r * math.sin(angle - math.pi / 2)
            points.append((int(x), int(y)))
        painter.drawPolygon(QPolygon([QPoint(x, y) for x, y in points]))

    def mousePressEvent(self, event):
        if not self._interactive:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            star_width = self.width() / self.max_stars
            clicked_star = int(event.position().x() / star_width) + 1
            clicked_star = max(1, min(clicked_star, self.max_stars))
            self.setValue(clicked_star)

    def mouseMoveEvent(self, event):
        if not self._interactive:
            return
        star_width = self.width() / self.max_stars
        hover_star = int(event.position().x() / star_width) + 1
        hover_star = max(0, min(hover_star, self.max_stars))
        if hover_star != self.hover_value:
            self.hover_value = hover_star
            self.update()

    def leaveEvent(self, event):
        self.hover_value = 0
        self.update()


class RatingPanel(QWidget):
    """评价编辑面板"""

    ratingScoreChanged = Signal(int, int)  # index, score
    ratingSchemaEdited = Signal()
    descriptionChanged = Signal(str)
    commentChanged = Signal(str)

    def __init__(self, card_model: Optional[CardModel] = None, parent=None):
        super().__init__(parent)
        self.card_model = card_model
        self._schema_edit_mode = False
        self._draft_names: list[str] = []
        self._row_widgets: list[dict] = []
        self._signals_connected = False
        self._create_ui()
        if card_model:
            self._connect_signals()
            self._connect_model_signals()
            self._refresh_from_model()

    def _create_ui(self):
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(8)

        rating_group = QFrame()
        rating_group.setFrameStyle(QFrame.Shape.Box)
        rating_group.setStyleSheet(RATING_GROUP_STYLE)
        rating_main_layout = QVBoxLayout(rating_group)
        rating_main_layout.setSpacing(0)
        rating_main_layout.setContentsMargins(0, 0, 0, 0)

        title_row = QWidget()
        title_row.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #4A90E2, stop:1 #357ABD); border: none; "
            "border-top-left-radius: 6px; border-top-right-radius: 6px;"
        )
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(12, 8, 8, 8)
        title_layout.setSpacing(8)

        self._rating_title_label = QLabel("评级 (1-5星)")
        self._rating_title_label.setStyleSheet(
            "color: white; font-weight: bold; font-size: 16px; background: transparent;"
        )
        title_layout.addWidget(self._rating_title_label)
        title_layout.addStretch()

        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setFixedSize(32, 32)
        self._settings_btn.setToolTip("编辑评价标准（名称与数量）")
        self._settings_btn.setStyleSheet(RATING_SETTINGS_BTN_STYLE)
        self._settings_btn.clicked.connect(self._toggle_schema_edit_mode)
        title_layout.addWidget(self._settings_btn)

        self._done_btn = QPushButton("完成")
        self._done_btn.setFixedHeight(28)
        self._done_btn.setStyleSheet(RATING_DONE_BTN_STYLE)
        self._done_btn.setVisible(False)
        self._done_btn.clicked.connect(self._exit_schema_edit_mode)
        title_layout.addWidget(self._done_btn)

        rating_main_layout.addWidget(title_row)

        rating_content_widget = QWidget()
        rating_content_widget.setStyleSheet(CONTENT_AREA_STYLE)
        rating_content_layout = QVBoxLayout(rating_content_widget)
        rating_content_layout.setContentsMargins(15, 15, 15, 15)
        rating_content_layout.setSpacing(8)

        self._rating_items_layout = QVBoxLayout()
        self._rating_items_layout.setSpacing(12)
        rating_content_layout.addLayout(self._rating_items_layout)

        self._empty_hint = QLabel("暂无评价维度，点击右上角设置添加")
        self._empty_hint.setStyleSheet("color: #7f8c8d; font-size: 13px;")
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rating_content_layout.addWidget(self._empty_hint)

        self._add_dim_btn = QPushButton("+ 添加维度")
        self._add_dim_btn.setStyleSheet(RATING_ADD_BTN_STYLE)
        self._add_dim_btn.setVisible(False)
        self._add_dim_btn.clicked.connect(self._add_dimension)
        rating_content_layout.addWidget(self._add_dim_btn)

        rating_main_layout.addWidget(rating_content_widget)
        layout.addWidget(rating_group)

        description_group = QFrame()
        description_group.setFrameStyle(QFrame.Shape.Box)
        description_group.setStyleSheet(DESCRIPTION_GROUP_STYLE)
        description_main_layout = QVBoxLayout(description_group)
        description_main_layout.setSpacing(0)
        description_main_layout.setContentsMargins(0, 0, 0, 0)

        description_title_label = QLabel("敌人描述")
        description_title_label.setStyleSheet(DESCRIPTION_TITLE_STYLE)
        description_main_layout.addWidget(description_title_label)

        description_content_widget = QWidget()
        description_content_widget.setStyleSheet(CONTENT_AREA_STYLE)
        description_content_layout = QVBoxLayout(description_content_widget)
        description_content_layout.setContentsMargins(15, 15, 15, 15)

        self.brief_description_edit = QTextEdit()
        self.brief_description_edit.setMinimumHeight(120)
        self.brief_description_edit.setMaximumHeight(160)
        self.brief_description_edit.setPlaceholderText("敌人的基本特点和能力描述...")
        self.brief_description_edit.setStyleSheet(DETAILED_TEXT_EDIT_STYLE)
        self._setup_text_edit_events(self.brief_description_edit, "敌人描述详细编辑")
        description_content_layout.addWidget(self.brief_description_edit)
        description_main_layout.addWidget(description_content_widget)
        layout.addWidget(description_group)

        comment_group = QFrame()
        comment_group.setFrameStyle(QFrame.Shape.Box)
        comment_group.setStyleSheet(COMMENT_GROUP_STYLE)
        comment_main_layout = QVBoxLayout(comment_group)
        comment_main_layout.setSpacing(0)
        comment_main_layout.setContentsMargins(0, 0, 0, 0)

        comment_title_label = QLabel("简要评价")
        comment_title_label.setStyleSheet(COMMENT_TITLE_STYLE)
        comment_main_layout.addWidget(comment_title_label)

        comment_content_widget = QWidget()
        comment_content_widget.setStyleSheet(CONTENT_AREA_STYLE)
        comment_content_layout = QVBoxLayout(comment_content_widget)
        comment_content_layout.setContentsMargins(15, 15, 15, 15)

        self.brief_comment_edit = QTextEdit()
        self.brief_comment_edit.setMinimumHeight(120)
        self.brief_comment_edit.setPlaceholderText("对敌人的整体评价...")
        self.brief_comment_edit.setStyleSheet(DETAILED_TEXT_EDIT_STYLE)
        self.brief_comment_edit.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.brief_comment_edit.installEventFilter(self)
        doc_layout = self.brief_comment_edit.document().documentLayout()
        doc_layout.documentSizeChanged.connect(
            lambda _size: self._adjust_brief_comment_height()
        )
        self._setup_text_edit_events(self.brief_comment_edit, "简要评价详细编辑")
        comment_content_layout.addWidget(self.brief_comment_edit)
        comment_main_layout.addWidget(comment_content_widget)

        layout.addWidget(comment_group)
        layout.addStretch()

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)

        self._syncing_ui = False
        self._desc_debouncer = FixedDebouncer(self, self._flush_description_changed, 280)
        self._comment_debouncer = FixedDebouncer(self, self._flush_comment_changed, 280)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)

        self._rebuild_rating_rows(get_rating_names(), default_rating_scores(len(get_rating_names())))

    def eventFilter(self, obj, event):
        if obj is self.brief_comment_edit and event.type() == QEvent.Type.Resize:
            self._adjust_brief_comment_height()
        return super().eventFilter(obj, event)

    def _adjust_brief_comment_height(self):
        te = self.brief_comment_edit
        w = te.viewport().width()
        if w <= 0:
            return
        doc = te.document()
        doc.setTextWidth(max(w, 50))
        doc_h = doc.size().height()
        m = te.contentsMargins()
        fw = te.frameWidth()
        pad = m.top() + m.bottom() + fw * 2 + 12
        line_h = te.fontMetrics().height()
        new_h = int(math.ceil(doc_h)) + pad
        te.setFixedHeight(max(120, new_h, line_h * 4))

    def _schedule_description_changed(self):
        if self._syncing_ui:
            return
        self._desc_debouncer.schedule()

    def _schedule_comment_changed(self):
        if self._syncing_ui:
            return
        self._comment_debouncer.schedule()

    def _flush_description_changed(self):
        self.descriptionChanged.emit(self.brief_description_edit.toPlainText())

    def _flush_comment_changed(self):
        self.commentChanged.emit(self.brief_comment_edit.toPlainText())

    def _clear_rating_rows(self) -> None:
        while self._rating_items_layout.count():
            item = self._rating_items_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._row_widgets.clear()

    def _rebuild_rating_rows(self, names: list[str], scores: list[int]) -> None:
        self._clear_rating_rows()
        aligned = align_rating_scores(scores, len(names))
        for i, name in enumerate(names):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            remove_btn = QPushButton("−")
            remove_btn.setFixedSize(28, 28)
            remove_btn.setStyleSheet(RATING_REMOVE_BTN_STYLE)
            remove_btn.setVisible(self._schema_edit_mode)
            remove_btn.clicked.connect(lambda _=False, idx=i: self._remove_dimension(idx))
            row_layout.addWidget(remove_btn)

            name_label = QLabel(name)
            name_label.setStyleSheet(RATING_LABEL_STYLE)
            name_label.setFixedWidth(110)
            name_label.setVisible(not self._schema_edit_mode)
            row_layout.addWidget(name_label)

            name_edit = QLineEdit(name)
            name_edit.setMaxLength(8)
            name_edit.setFixedWidth(110)
            name_edit.setStyleSheet(RATING_NAME_EDIT_STYLE)
            name_edit.setVisible(self._schema_edit_mode)
            name_edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            name_edit.textChanged.connect(lambda text, idx=i: self._on_draft_name_changed(idx, text))
            row_layout.addWidget(name_edit)

            star = StarRatingWidget(5, aligned[i] if i < len(aligned) else 3)
            star.setInteractive(not self._schema_edit_mode)
            star.valueChanged.connect(lambda value, idx=i: self._on_score_changed(idx, value))
            row_layout.addWidget(star)
            row_layout.addStretch()

            self._rating_items_layout.addWidget(row)
            self._row_widgets.append(
                {
                    "row": row,
                    "remove_btn": remove_btn,
                    "name_label": name_label,
                    "name_edit": name_edit,
                    "star": star,
                }
            )

        self._empty_hint.setVisible(len(names) == 0)
        self._add_dim_btn.setVisible(self._schema_edit_mode)
        self._add_dim_btn.setEnabled(len(names) < MAX_RATING_DIMENSIONS)
        self._update_title_hint()

    def _update_title_hint(self) -> None:
        if self._schema_edit_mode:
            self._rating_title_label.setText(
                f"编辑评价标准 (0-{MAX_RATING_DIMENSIONS})"
            )
        else:
            n = len(self._row_widgets)
            self._rating_title_label.setText(f"评级 ({n}项 · 1-5星)")

    def _apply_edit_mode_chrome(self) -> None:
        self._settings_btn.setVisible(not self._schema_edit_mode)
        self._done_btn.setVisible(self._schema_edit_mode)
        self._add_dim_btn.setVisible(self._schema_edit_mode)
        self._add_dim_btn.setEnabled(len(self._draft_names) < MAX_RATING_DIMENSIONS)
        for row in self._row_widgets:
            row["remove_btn"].setVisible(self._schema_edit_mode)
            row["name_label"].setVisible(not self._schema_edit_mode)
            row["name_edit"].setVisible(self._schema_edit_mode)
            row["star"].setInteractive(not self._schema_edit_mode)
        self._update_title_hint()

    def _toggle_schema_edit_mode(self) -> None:
        if self._schema_edit_mode:
            self._exit_schema_edit_mode()
        else:
            self._enter_schema_edit_mode()

    def _enter_schema_edit_mode(self) -> None:
        self._schema_edit_mode = True
        self._draft_names = list(get_rating_names())
        scores = (
            list(self.card_model.enemy_data.rating_scores)
            if self.card_model
            else default_rating_scores(len(self._draft_names))
        )
        self._rebuild_rating_rows(self._draft_names, scores)
        self._apply_edit_mode_chrome()

    def _exit_schema_edit_mode(self) -> None:
        names: list[str] = []
        for row in self._row_widgets:
            text = row["name_edit"].text().strip()
            if not text:
                text = "未命名"
            names.append(text[:8])
        try:
            schema = RatingSchema(names=names)
            save_rating_schema(schema)
        except Exception:
            # 校验失败时仍退出编辑，回退磁盘/默认标准
            load_rating_schema(force_reload=True)
        self._schema_edit_mode = False
        self._draft_names = list(get_rating_names())
        self.ratingSchemaEdited.emit()
        if self.card_model:
            scores = align_rating_scores(
                list(self.card_model.enemy_data.rating_scores),
                len(self._draft_names),
            )
        else:
            scores = default_rating_scores(len(self._draft_names))
        self._rebuild_rating_rows(self._draft_names, scores)
        self._apply_edit_mode_chrome()

    def _on_draft_name_changed(self, index: int, text: str) -> None:
        if 0 <= index < len(self._draft_names):
            self._draft_names[index] = text

    def _add_dimension(self) -> None:
        if len(self._draft_names) >= MAX_RATING_DIMENSIONS:
            return
        self._draft_names.append(f"维度{len(self._draft_names) + 1}")
        scores = (
            align_rating_scores(
                list(self.card_model.enemy_data.rating_scores),
                len(self._draft_names),
            )
            if self.card_model
            else default_rating_scores(len(self._draft_names))
        )
        self._rebuild_rating_rows(self._draft_names, scores)
        self._apply_edit_mode_chrome()

    def _remove_dimension(self, index: int) -> None:
        if index < 0 or index >= len(self._draft_names):
            return
        del self._draft_names[index]
        scores = (
            align_rating_scores(
                list(self.card_model.enemy_data.rating_scores),
                len(self._draft_names),
            )
            if self.card_model
            else default_rating_scores(len(self._draft_names))
        )
        # 编辑模式下删除后分数仅用于 UI 占位展示，不写回敌人
        self._rebuild_rating_rows(self._draft_names, scores)
        self._apply_edit_mode_chrome()

    def _on_score_changed(self, index: int, value: int) -> None:
        if self._syncing_ui or self._schema_edit_mode:
            return
        self.ratingScoreChanged.emit(index, value)

    def _connect_signals(self):
        if self._signals_connected:
            return
        self.brief_description_edit.textChanged.connect(self._schedule_description_changed)
        self.brief_comment_edit.textChanged.connect(self._schedule_comment_changed)
        self._signals_connected = True

    def _connect_model_signals(self):
        if not self.card_model:
            return
        self.card_model.ratingSchemaChanged.connect(self._refresh_from_model)

    def set_card_model(self, card_model: CardModel):
        self.card_model = card_model
        self._connect_signals()
        self._connect_model_signals()
        self._refresh_from_model()

    def _refresh_from_model(self):
        if not self.card_model:
            return
        if self._schema_edit_mode:
            return

        self._desc_debouncer.stop()
        self._comment_debouncer.stop()
        self._syncing_ui = True
        try:
            data = self.card_model.enemy_data
            names = get_rating_names()
            scores = align_rating_scores(list(data.rating_scores), len(names))
            self._rebuild_rating_rows(names, scores)
            self._apply_edit_mode_chrome()

            self.brief_description_edit.setPlainText(data.brief_description)
            self.brief_comment_edit.setPlainText(data.brief_comment)
            self._adjust_brief_comment_height()
        finally:
            self._syncing_ui = False

    def refresh_from_model(self):
        self._refresh_from_model()

    def _setup_text_edit_events(self, text_edit: QTextEdit, dialog_title: str):
        def contextMenuEvent(event):
            menu = text_edit.createStandardContextMenu()
            menu.addSeparator()
            detailed_edit_action = menu.addAction("详细编辑")
            detailed_edit_action.triggered.connect(
                lambda: self._open_detailed_editor(text_edit, dialog_title)
            )
            menu.exec_(event.globalPos())
            event.accept()

        text_edit.contextMenuEvent = contextMenuEvent

    def _open_detailed_editor(self, text_edit: QTextEdit, dialog_title: str):
        current_text = text_edit.toPlainText()
        placeholder = text_edit.placeholderText()
        accepted, new_text = DetailedEditorDialog.edit_text(
            title=dialog_title,
            initial_text=current_text,
            placeholder=placeholder,
            parent=self,
        )
        if accepted:
            text_edit.setPlainText(new_text)
