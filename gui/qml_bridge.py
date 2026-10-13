"""QML 与现有模型、渲染协调器之间的唯一桥接层。"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtWidgets import QFileDialog, QWidget

from models import DEFAULT_RATING_SCORE, RatingSchema, scores_for_rating_draft
from utils.app_identity import APP_NAME, APP_SUMMARY
from utils.app_settings_store import (
    ai_base_url_preview,
    ai_request_config,
    current_render_options,
    is_rating_radar,
    load_app_settings,
    recent_files,
    save_ai_settings,
    save_rating_schema,
    set_rating_radar,
    set_update_check_enabled,
)
from utils.app_version import get_app_build_time, get_app_version
from utils.error_handler import FileOperationError
from utils.resource_manager import resource_manager

from .card_model import CardModel
from .render_coordinator import RenderCoordinator
from .skill_list_model import SkillListModel

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
    ratingRadarChanged = Signal(bool)
    previewChanged = Signal(int)
    busyChanged = Signal(bool)
    prtsBusyChanged = Signal(bool)
    recentFilesChanged = Signal(str)
    messageChanged = Signal(str, str)
    fieldError = Signal(str, str)
    dialogRequested = Signal(str, str, str)
    newRequested = Signal()
    openRequested = Signal()
    openRecentRequested = Signal(str)
    removeRecentRequested = Signal(str)
    removeRecentConfirmRequested = Signal(str, str)
    clearRecentRequested = Signal()
    saveRequested = Signal()
    exportRequested = Signal()
    refreshRequested = Signal()
    quitRequested = Signal()
    prtsQueryRequested = Signal(str)
    prtsLevelsChanged = Signal()
    prtsLevelChangeRequested = Signal(int)
    aboutRequested = Signal()
    lightDismissRequested = Signal()
    undoStateChanged = Signal()
    updateBannerChanged = Signal()
    updateCheckEnabledChanged = Signal()
    checkUpdatesRequested = Signal()
    dismissUpdateRequested = Signal(str)
    aiSettingsChanged = Signal()
    aiSettingsRequested = Signal()

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
        self._skills = SkillListModel(card_model, parent=self)
        self._busy = False
        self._prts_busy = False
        self._prts_levels: list[dict] = []
        self._preview_revision = 0
        self._update_banner_tag = ""
        self._update_banner_url = ""
        self._connect_card_model()
        self._render.cardReady.connect(self._on_card_ready)
        self._render.busyChanged.connect(self._set_busy)

    @Property(str, notify=enemyDataChanged)
    def enemyDataJson(self) -> str:  # noqa: N802
        return self._card_model.enemy_data.model_dump_json(
            ensure_ascii=False, exclude={"skills"}
        )

    @Property(QObject, constant=True)
    def skills(self) -> SkillListModel:
        return self._skills

    @Property(bool, notify=ratingRadarChanged)
    def ratingRadar(self) -> bool:  # noqa: N802
        return is_rating_radar()

    @Property(int, constant=True)
    def defaultRatingScore(self) -> int:  # noqa: N802
        """评价维度缺位时的补分，与 models.rating_schema 的默认值同源。"""
        return DEFAULT_RATING_SCORE

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=prtsBusyChanged)
    def prtsBusy(self) -> bool:  # noqa: N802
        return self._prts_busy

    @Property(str, notify=prtsLevelsChanged)
    def prtsLevelsJson(self) -> str:  # noqa: N802
        """本次导入上下文里的级别列表（JSON 数组）；未导入或已换卡时为空数组。"""
        return json.dumps(self._prts_levels, ensure_ascii=False)

    @Property(int, notify=prtsLevelsChanged)
    def prtsLevelIndex(self) -> int:  # noqa: N802
        """当前卡数据取自哪一级别；由卡片模型持有，随撤销栈快照回放。"""
        return self._card_model.prts_level_index

    @Property(str, notify=recentFilesChanged)
    def recentFilesJson(self) -> str:  # noqa: N802
        """最近打开或保存过的配置；名称与可用性随列表交给界面。"""
        return json.dumps(
            [
                {"path": path, "name": Path(path).name, "exists": Path(path).is_file()}
                for path in recent_files()
            ],
            ensure_ascii=False,
        )

    @Property(int, notify=previewChanged)
    def previewRevision(self) -> int:  # noqa: N802
        return self._preview_revision

    @Property(str, constant=True)
    def appIconUrl(self) -> str:  # noqa: N802
        return QUrl.fromLocalFile(
            resource_manager.get_resource_path("resource/icon.png")
        ).toString()

    @Property(str, constant=True)
    def appName(self) -> str:  # noqa: N802
        return APP_NAME

    @Property(str, constant=True)
    def appSummary(self) -> str:  # noqa: N802
        return APP_SUMMARY

    @Property(str, constant=True)
    def appVersion(self) -> str:  # noqa: N802
        return get_app_version()

    @Property(str, constant=True)
    def appBuildTime(self) -> str:  # noqa: N802
        return get_app_build_time() or ""

    @Property(str, notify=updateBannerChanged)
    def updateBannerTag(self) -> str:  # noqa: N802
        return self._update_banner_tag

    @Property(str, notify=updateBannerChanged)
    def updateBannerUrl(self) -> str:  # noqa: N802
        return self._update_banner_url

    @Property(bool, notify=updateCheckEnabledChanged)
    def updateCheckEnabled(self) -> bool:  # noqa: N802
        return load_app_settings().update_check_enabled

    @Property(str, notify=aiSettingsChanged)
    def aiBaseUrl(self) -> str:  # noqa: N802
        """AI 设置框的预填值；随保存变更信号刷新。"""
        return load_app_settings().ai_base_url

    @Property(str, notify=aiSettingsChanged)
    def aiModel(self) -> str:  # noqa: N802
        """AI 设置框的预填值；随保存变更信号刷新。"""
        return load_app_settings().ai_model

    @Property(str, notify=aiSettingsChanged)
    def aiApiKey(self) -> str:  # noqa: N802
        """AI 设置框的预填值；随保存变更信号刷新。"""
        return load_app_settings().ai_api_key

    @Property(bool, notify=aiSettingsChanged)
    def aiConfigured(self) -> bool:  # noqa: N802
        """Base URL / 模型 / 密钥是否齐备；判定与调用层同源。"""
        return ai_request_config() is not None

    def set_update_banner(self, tag: str, url: str) -> None:
        """把是否显示横幅的结果交给界面。标签为空则不显示。"""
        if tag == self._update_banner_tag and url == self._update_banner_url:
            return
        self._update_banner_tag = tag
        self._update_banner_url = url
        self.updateBannerChanged.emit()

    def set_card_model(self, card_model: CardModel) -> None:
        """在新建卡片后切换数据源，避免 QML 持有过期模型。"""
        self._disconnect_card_model()
        self._card_model = card_model
        self._connect_card_model()
        self._skills.set_card_model(card_model)
        self._publish_model()
        self.undoStateChanged.emit()

    @Property(bool, notify=undoStateChanged)
    def canUndo(self) -> bool:  # noqa: N802
        return self._card_model.undo_stack().canUndo()

    @Property(bool, notify=undoStateChanged)
    def canRedo(self) -> bool:  # noqa: N802
        return self._card_model.undo_stack().canRedo()

    def _connect_card_model(self) -> None:
        self._card_model.snapshotChanged.connect(self._publish_model)
        self._card_model.validationFailed.connect(self.fieldError)
        self._card_model.prtsLevelChanged.connect(self._publish_prts_levels)
        stack = self._card_model.undo_stack()
        stack.canUndoChanged.connect(self._publish_undo_state)
        stack.canRedoChanged.connect(self._publish_undo_state)

    def _disconnect_card_model(self) -> None:
        stack = self._card_model.undo_stack()
        for signal, slot in (
            (self._card_model.snapshotChanged, self._publish_model),
            (self._card_model.validationFailed, self.fieldError),
            (self._card_model.prtsLevelChanged, self._publish_prts_levels),
            (stack.canUndoChanged, self._publish_undo_state),
            (stack.canRedoChanged, self._publish_undo_state),
        ):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass

    def _publish_model(self) -> None:
        self.enemyDataChanged.emit(self.enemyDataJson)

    def _publish_undo_state(self, _available: bool) -> None:
        self.undoStateChanged.emit()

    def _publish_prts_levels(self, _level_index: int) -> None:
        """级别来源变化（导入、切换、撤销回放）后刷新界面；列表与编号由 QML 各自读取。"""
        self.prtsLevelsChanged.emit()

    def _set_busy(self, busy: bool) -> None:
        if self._busy != busy:
            self._busy = busy
            self.busyChanged.emit(busy)

    def set_prts_busy(self, busy: bool) -> None:
        if self._prts_busy != busy:
            self._prts_busy = busy
            self.prtsBusyChanged.emit(busy)

    def set_prts_levels(self, levels: list[dict]) -> None:
        """主窗口在导入成功后同步级别列表；传空表即清除（当前级别由卡片模型提供）。"""
        self._prts_levels = [dict(item) for item in levels]
        self.prtsLevelsChanged.emit()

    def show_dialog(self, title: str, message: str, tone: str = "info") -> None:
        """请求 QML 使用统一的应用内弹窗展示消息。"""
        self.dialogRequested.emit(title, message, tone)

    def show_toast(self, message: str, tone: str = "info") -> None:
        """非阻塞反馈使用短暂提示；tone 取 info / success / warning / error，配色与图标由界面映射。"""
        self.messageChanged.emit(message, tone)

    def refresh_recent_files(self) -> None:
        """最近列表发生变化后，把最新列表一并推给界面。"""
        self.recentFilesChanged.emit(self.recentFilesJson)

    def confirm_remove_recent(self, path: str) -> None:
        """最近项的文件已不存在时，请求界面确认是否移除该记录（不弹报错）。"""
        self.removeRecentConfirmRequested.emit(path, Path(path).name)

    def _on_card_ready(self, result: object, _revision: int) -> None:
        if isinstance(result, QPixmap):
            self._image_provider.set_pixmap(result)
            self._preview_revision += 1
            self.previewChanged.emit(self._preview_revision)

    @Slot(str, str)
    def updateProperty(self, property_name: str, value_json: str) -> None:  # noqa: N802
        """按 JSON 标量更新单个 Pydantic 字段。"""
        try:
            value = json.loads(value_json)
        except json.JSONDecodeError:
            self.fieldError.emit(property_name, "输入格式无效")
            return
        self._card_model.update_property(property_name, value)

    @Slot(str)
    def updateProperties(self, values_json: str) -> None:  # noqa: N802
        """按 JSON 对象一次写入多个字段。"""
        try:
            values = json.loads(values_json)
        except json.JSONDecodeError:
            self.fieldError.emit("properties", "输入格式无效")
            return
        if not isinstance(values, dict):
            self.fieldError.emit("properties", "输入格式无效")
            return
        self._card_model.update_properties(values)

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
        except FileOperationError as error:
            self.fieldError.emit("rating_display", str(error))
            self.ratingRadarChanged.emit(is_rating_radar())
            return
        self.ratingRadarChanged.emit(bool(enabled))
        self._render.request(self._card_model.enemy_data, current_render_options())

    @Slot(str, bool, result=bool)
    def updateRatingSchema(self, draft_json: str, save_template: bool) -> bool:  # noqa: N802
        """把草稿套到当前卡的内存。save_template 为真时同时写入新建模板。不写卡片配置。"""
        try:
            raw = json.loads(draft_json)
            if not isinstance(raw, list):
                raise ValueError("评价标准格式无效")
            draft_ids: list[str] = []
            names: list[str] = []
            for item in raw:
                if not isinstance(item, dict):
                    raise ValueError("评价标准格式无效")
                draft_ids.append(str(item.get("id", "")))
                names.append(str(item.get("name", "")).strip()[:8] or "未命名")
            schema = RatingSchema(names=names)
            scores = scores_for_rating_draft(
                [item.score for item in self._card_model.enemy_data.ratings],
                draft_ids,
            )
            next_enemy = self._card_model.enemy_with_ratings(list(schema.names), scores)
            if save_template:
                save_rating_schema(schema)
            self._card_model.apply_enemy_data(next_enemy)
        except (FileOperationError, TypeError, ValueError, json.JSONDecodeError) as error:
            self.fieldError.emit("rating_schema", str(error))
            return False
        return True

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
    def requestUndo(self) -> None:  # noqa: N802
        self._card_model.undo_stack().undo()

    @Slot()
    def requestRedo(self) -> None:  # noqa: N802
        self._card_model.undo_stack().redo()

    @Slot()
    def requestNew(self) -> None:  # noqa: N802
        self.newRequested.emit()

    @Slot()
    def requestOpen(self) -> None:  # noqa: N802
        self.openRequested.emit()

    @Slot(str)
    def requestOpenRecent(self, path: str) -> None:  # noqa: N802
        self.openRecentRequested.emit(path)

    @Slot(str)
    def requestRemoveRecent(self, path: str) -> None:  # noqa: N802
        self.removeRecentRequested.emit(path)

    @Slot()
    def requestClearRecent(self) -> None:  # noqa: N802
        self.clearRecentRequested.emit()

    @Slot()
    def requestSave(self) -> None:  # noqa: N802
        self.saveRequested.emit()

    @Slot()
    def requestExport(self) -> None:  # noqa: N802
        self.exportRequested.emit()

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

    @Slot(int)
    def requestPrtsLevelChange(self, level_index: int) -> None:  # noqa: N802
        """请求把当前卡切换到该级别；没有导入上下文或级别不在表内时忽略。"""
        if not self._prts_levels:
            return
        if all(item.get("index") != level_index for item in self._prts_levels):
            return
        self.prtsLevelChangeRequested.emit(int(level_index))

    @Slot()
    def requestAbout(self) -> None:  # noqa: N802
        self.aboutRequested.emit()

    @Slot()
    def requestAiSettings(self) -> None:  # noqa: N802
        self.aiSettingsRequested.emit()

    @Slot()
    def requestCheckUpdates(self) -> None:  # noqa: N802
        self.checkUpdatesRequested.emit()

    @Slot(str)
    def dismissUpdate(self, tag: str) -> None:  # noqa: N802
        self.dismissUpdateRequested.emit(tag)

    @Slot(bool)
    def setUpdateCheckEnabled(self, enabled: bool) -> None:  # noqa: N802
        set_update_check_enabled(enabled)
        self.updateCheckEnabledChanged.emit()

    @Slot(str, result=str)
    def aiBaseUrlPreview(self, base_url: str) -> str:  # noqa: N802
        """该地址最终请求到的完整 URL；只用于显示，不阻止保存。"""
        return ai_base_url_preview(base_url)

    @Slot(str, str, str, result=bool)
    def saveAiSettings(self, base_url: str, model: str, api_key: str) -> bool:  # noqa: N802
        """写入 AI 配置。形状非法或写盘失败时发字段错误并返回 False，界面据此保持打开。"""
        try:
            save_ai_settings(base_url, model, api_key)
        except (ValueError, FileOperationError) as error:
            self.fieldError.emit("ai_settings", str(error))
            return False
        self.aiSettingsChanged.emit()
        self.show_toast("AI 配置已保存", "success")
        return True
