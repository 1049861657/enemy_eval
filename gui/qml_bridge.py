"""QML 与现有模型、渲染协调器之间的唯一桥接层。"""

from __future__ import annotations

import json
from threading import Lock

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtWidgets import QFileDialog, QWidget

from models import RatingSchema, SkillEntry
from utils.rating_schema_store import (
    get_rating_names,
    is_rating_radar,
    save_rating_schema,
    set_rating_radar,
)

from .card_model import CardModel
from .render_coordinator import RenderCoordinator

class CardImageProvider(QQuickImageProvider):
    """将渲染线程交付到主线程的预览图提供给 QML Image。"""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._image = QImage()
        self._lock = Lock()

    def set_pixmap(self, pixmap: QPixmap) -> None:
        with self._lock:
            self._image = pixmap.toImage()

    def requestImage(self, image_id: str, size, requested_size) -> QImage:  # noqa: N802
        del image_id
        with self._lock:
            image = self._image.copy()
        if not image.isNull() and requested_size.width() > 0 and requested_size.height() > 0:
            image = image.scaled(requested_size)
        if size is not None:
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image


class QmlBridge(QObject):
    """暴露稳定、显式的 QML 属性、信号和槽，不泄露 Pydantic 对象。"""

    enemyDataChanged = Signal(str)
    ratingNamesChanged = Signal(str)
    ratingRadarChanged = Signal(bool)
    previewChanged = Signal(int)
    busyChanged = Signal(bool)
    prtsBusyChanged = Signal(bool)
    messageChanged = Signal(str)
    fieldError = Signal(str, str)
    renderError = Signal(str)
    dialogRequested = Signal(str, str, str)
    newRequested = Signal()
    openRequested = Signal()
    saveRequested = Signal()
    exportRequested = Signal()
    resetRequested = Signal()
    refreshRequested = Signal()
    quitRequested = Signal()
    prtsQueryRequested = Signal(str)
    aboutRequested = Signal()

    def __init__(
        self,
        card_model: CardModel,
        render: RenderCoordinator,
        image_provider: CardImageProvider,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._card_model = card_model
        self._render = render
        self._image_provider = image_provider
        self._busy = False
        self._prts_busy = False
        self._preview_revision = 0
        self._connect_card_model()
        self._render.cardReady.connect(self._on_card_ready)
        self._render.renderFailed.connect(self._on_render_failed)
        self._render.busyChanged.connect(self._set_busy)

    @Property(str, notify=enemyDataChanged)
    def enemyDataJson(self) -> str:  # noqa: N802
        return json.dumps(self._card_model.get_current_dict(), ensure_ascii=False)

    @Property(str, notify=ratingNamesChanged)
    def ratingNamesJson(self) -> str:  # noqa: N802
        return json.dumps(get_rating_names(), ensure_ascii=False)

    @Property(bool, notify=ratingRadarChanged)
    def ratingRadar(self) -> bool:  # noqa: N802
        return is_rating_radar()

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=prtsBusyChanged)
    def prtsBusy(self) -> bool:  # noqa: N802
        return self._prts_busy

    @Property(int, notify=previewChanged)
    def previewRevision(self) -> int:  # noqa: N802
        return self._preview_revision

    def set_card_model(self, card_model: CardModel) -> None:
        """在新建卡片后切换数据源，避免 QML 持有过期模型。"""
        self._disconnect_card_model()
        self._card_model = card_model
        self._connect_card_model()
        self._publish_model()

    def _connect_card_model(self) -> None:
        self._card_model.dataChanged.connect(self._publish_model)
        self._card_model.validationFailed.connect(self.fieldError)
        self._card_model.ratingSchemaChanged.connect(self._publish_rating_schema)

    def _disconnect_card_model(self) -> None:
        for signal, slot in (
            (self._card_model.dataChanged, self._publish_model),
            (self._card_model.validationFailed, self.fieldError),
            (self._card_model.ratingSchemaChanged, self._publish_rating_schema),
        ):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass

    def _publish_model(self) -> None:
        self.enemyDataChanged.emit(self.enemyDataJson)

    def _publish_rating_schema(self) -> None:
        self.ratingNamesChanged.emit(self.ratingNamesJson)
        self._publish_model()

    def _set_busy(self, busy: bool) -> None:
        if self._busy != busy:
            self._busy = busy
            self.busyChanged.emit(busy)

    def set_prts_busy(self, busy: bool) -> None:
        if self._prts_busy != busy:
            self._prts_busy = busy
            self.prtsBusyChanged.emit(busy)

    def show_dialog(self, title: str, message: str, tone: str = "info") -> None:
        """请求 QML 使用统一的应用内弹窗展示消息。"""
        self.dialogRequested.emit(title, message, tone)

    def show_toast(self, message: str) -> None:
        """非阻塞反馈使用短暂提示，不中断当前操作。"""
        self.messageChanged.emit(message)

    def _on_card_ready(self, result: object, _revision: int) -> None:
        if isinstance(result, QPixmap):
            self._image_provider.set_pixmap(result)
            self._preview_revision += 1
            self.previewChanged.emit(self._preview_revision)

    def _on_render_failed(self, message: str) -> None:
        self.renderError.emit(message)

    @Slot(str, str)
    def updateProperty(self, property_name: str, value_json: str) -> None:  # noqa: N802
        """按 JSON 标量更新单个 Pydantic 字段。"""
        try:
            value = json.loads(value_json)
        except json.JSONDecodeError:
            self.fieldError.emit(property_name, "输入格式无效")
            return
        self._card_model.update_property(property_name, value)

    @Slot(str, float)
    def updateResistance(self, resistance_name: str, value: float) -> None:  # noqa: N802
        self._card_model.update_abnormal_resistance(resistance_name, value)

    @Slot(int, int)
    def updateRatingScore(self, index: int, score: int) -> None:  # noqa: N802
        self._card_model.update_rating_score(index, score)

    @Slot(bool)
    def setRatingRadar(self, enabled: bool) -> None:  # noqa: N802
        if is_rating_radar() == bool(enabled):
            return
        try:
            set_rating_radar(bool(enabled))
        except RuntimeError as error:
            self.fieldError.emit("rating_display", str(error))
            self.ratingRadarChanged.emit(is_rating_radar())
            return
        self.ratingRadarChanged.emit(bool(enabled))
        self._render.request(self._card_model.enemy_data)

    @Slot(str)
    def updateRatingSchema(self, names_json: str) -> None:  # noqa: N802
        try:
            names = [
                str(name).strip()[:8] or "未命名"
                for name in json.loads(names_json)
            ]
            schema = RatingSchema(names=names)
            save_rating_schema(schema)
            self._card_model.realign_rating_scores_to_schema()
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            self.fieldError.emit("rating_schema", str(error))

    @Slot(int, str)
    def updateSkill(self, index: int, skill_json: str) -> None:  # noqa: N802
        try:
            self._card_model.update_skill(index, SkillEntry.model_validate(json.loads(skill_json)))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            self.fieldError.emit("skills", str(error))

    @Slot()
    def addSkill(self) -> None:  # noqa: N802
        skills = [skill.model_dump() for skill in self._card_model.enemy_data.skills]
        skills.append(SkillEntry().model_dump())
        self._card_model.update_property("skills", skills)

    @Slot(int)
    def removeSkill(self, index: int) -> None:  # noqa: N802
        skills = list(self._card_model.enemy_data.skills)
        if 0 <= index < len(skills):
            del skills[index]
            self._card_model.update_property("skills", skills)

    @Slot()
    def chooseAvatar(self) -> None:  # noqa: N802
        parent = self.parent()
        widget_parent = parent if isinstance(parent, QWidget) else None
        path, _ = QFileDialog.getOpenFileName(
            widget_parent, "选择头像", "", "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
        )
        if path:
            self._card_model.update_property("avatar_path", path)

    @Slot()
    def requestNew(self) -> None:  # noqa: N802
        self.newRequested.emit()

    @Slot()
    def requestOpen(self) -> None:  # noqa: N802
        self.openRequested.emit()

    @Slot()
    def requestSave(self) -> None:  # noqa: N802
        self.saveRequested.emit()

    @Slot()
    def requestExport(self) -> None:  # noqa: N802
        self.exportRequested.emit()

    @Slot()
    def requestReset(self) -> None:  # noqa: N802
        self.resetRequested.emit()

    @Slot()
    def requestRefresh(self) -> None:  # noqa: N802
        self.refreshRequested.emit()

    @Slot()
    def requestQuit(self) -> None:  # noqa: N802
        self.quitRequested.emit()

    @Slot(str)
    def requestPrtsQuery(self, enemy_name: str) -> None:  # noqa: N802
        if enemy_name.strip():
            self.prtsQueryRequested.emit(enemy_name.strip())

    @Slot()
    def requestAbout(self) -> None:  # noqa: N802
        self.aboutRequested.emit()
