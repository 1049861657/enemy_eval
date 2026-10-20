"""QML 桥接层：只声明 QML 可见的信号、属性与槽，逻辑按域落在 `gui/bridge/`。

QML 按名调用：QML 可见名、信号签名、provider id `enemy-card` 及查询参数 `revision` 都不得改名——
改名不会编译报错，只在运行时静默失效。Qt 元对象必须声明在本类上（PySide6 不支持从非 QObject
mixin 继承元对象），故域实现是普通函数/小类，本类只做一行转发与信号发射。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget

from models import DEFAULT_RATING_SCORE, AiEvaluationResult
from utils.app.render_prefs import is_rating_radar
from utils.errors import FileOperationError

from .bridge import ai, app, editor, files, prts
from .bridge.model_link import CardModelLink
from .skill_list_model import SkillListModel

if TYPE_CHECKING:
    from .bridge.preview import CardImageProvider
    from .card_model import CardModel
    from .render_coordinator import RenderCoordinator


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
    undoStateChanged = Signal()
    updateBannerChanged = Signal()
    updateCheckEnabledChanged = Signal()
    checkUpdatesRequested = Signal()
    dismissUpdateRequested = Signal(str)
    aiSettingsChanged = Signal()
    aiSettingsRequested = Signal()
    aiBusyChanged = Signal()
    aiReviewRequested = Signal(object, object, object, object, int)
    aiCommentReady = Signal()
    aiCommentConfirmRequested = Signal(str)
    aiAbandonRequested = Signal()

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
        self._link = CardModelLink(
            on_model_changed=self._publish_model,
            on_field_error=self._emit_field_error,
            on_level_changed=self._publish_prts_levels,
            on_undo_state=self._publish_undo_state,
        )
        self._session = ai.ReviewSession()
        self._busy = False
        self._prts_busy = False
        self._ai_busy = False
        self._prts_levels: list[dict] = []
        self._preview_revision = 0
        self._update_banner_tag = ""
        self._update_banner_url = ""
        self._link.attach(card_model)
        self._render.cardReady.connect(self._on_card_ready)
        self._render.busyChanged.connect(self._set_busy)

    # ---- 属性 ----

    @Property(str, notify=enemyDataChanged)
    def enemyDataJson(self) -> str:  # noqa: N802
        return editor.enemy_data_json(self._card_model)

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
        return prts.levels_json(self._prts_levels)

    @Property(int, notify=prtsLevelsChanged)
    def prtsLevelIndex(self) -> int:  # noqa: N802
        """当前卡数据取自哪一级别；由卡片模型持有，随撤销栈快照回放。"""
        return self._card_model.prts_level_index

    @Property(str, notify=recentFilesChanged)
    def recentFilesJson(self) -> str:  # noqa: N802
        """最近打开或保存过的配置；名称与可用性随列表交给界面。"""
        return files.recent_files_json()

    @Property(int, notify=previewChanged)
    def previewRevision(self) -> int:  # noqa: N802
        return self._preview_revision

    @Property(str, constant=True)
    def appIconUrl(self) -> str:  # noqa: N802
        return app.app_icon_url()

    @Property(str, constant=True)
    def appName(self) -> str:  # noqa: N802
        return app.app_name()

    @Property(str, constant=True)
    def appSummary(self) -> str:  # noqa: N802
        return app.app_summary()

    @Property(str, constant=True)
    def appVersion(self) -> str:  # noqa: N802
        return app.app_version()

    @Property(str, constant=True)
    def appBuildTime(self) -> str:  # noqa: N802
        return app.app_build_time()

    @Property(str, notify=updateBannerChanged)
    def updateBannerTag(self) -> str:  # noqa: N802
        return self._update_banner_tag

    @Property(str, notify=updateBannerChanged)
    def updateBannerUrl(self) -> str:  # noqa: N802
        return self._update_banner_url

    @Property(bool, notify=updateCheckEnabledChanged)
    def updateCheckEnabled(self) -> bool:  # noqa: N802
        return app.update_check_enabled()

    @Property(str, notify=aiSettingsChanged)
    def aiBaseUrl(self) -> str:  # noqa: N802
        """AI 设置框的预填值；随保存变更信号刷新。"""
        return ai.base_url()

    @Property(str, notify=aiSettingsChanged)
    def aiModel(self) -> str:  # noqa: N802
        """AI 设置框的预填值；随保存变更信号刷新。"""
        return ai.model()

    @Property(str, notify=aiSettingsChanged)
    def aiApiKey(self) -> str:  # noqa: N802
        """AI 设置框的预填值；随保存变更信号刷新。"""
        return ai.api_key()

    @Property(bool, notify=aiSettingsChanged)
    def aiConfigured(self) -> bool:  # noqa: N802
        """Base URL / 模型 / 密钥是否齐备；判定与调用层同源。"""
        return ai.configured()

    @Property(bool, notify=aiBusyChanged)
    def aiBusy(self) -> bool:  # noqa: N802
        """评价请求在飞；顶栏按钮与弹窗按钮据此禁用。"""
        return self._ai_busy

    @Property(str, notify=aiCommentReady)
    def aiComment(self) -> str:  # noqa: N802
        """最近一次成功的简评正文；超长不裁剪。"""
        return self._session.comment

    @Property(bool, notify=undoStateChanged)
    def canUndo(self) -> bool:  # noqa: N802
        return self._card_model.undo_stack().canUndo()

    @Property(bool, notify=undoStateChanged)
    def canRedo(self) -> bool:  # noqa: N802
        return self._card_model.undo_stack().canRedo()

    # ---- 编辑槽 ----

    @Slot(str, str)
    def updateProperty(self, property_name: str, value_json: str) -> None:  # noqa: N802
        """按 JSON 标量更新单个 Pydantic 字段。"""
        editor.update_property(self._card_model, property_name, value_json, self._emit_field_error)

    @Slot(str)
    def updateProperties(self, values_json: str) -> None:  # noqa: N802
        """按 JSON 对象一次写入多个字段。"""
        editor.update_properties(self._card_model, values_json, self._emit_field_error)

    @Slot(str, float)
    def updateResistance(self, resistance_name: str, value: float) -> None:  # noqa: N802
        editor.update_resistance(self._card_model, resistance_name, value)

    @Slot(int, int)
    def updateRatingScore(self, index: int, score: int) -> None:  # noqa: N802
        editor.update_rating_score(self._card_model, index, score)

    @Slot(bool)
    def setRatingRadar(self, enabled: bool) -> None:  # noqa: N802
        """切换雷达/记分板并重绘；写盘失败回滚界面状态。"""
        editor.set_rating_radar_pref(
            self._card_model,
            self._render,
            enabled,
            self._emit_field_error,
            self.ratingRadarChanged.emit,
        )

    @Slot(str, bool, result=bool)
    def updateRatingSchema(self, draft_json: str, save_template: bool) -> bool:  # noqa: N802
        """把草稿套到当前卡的内存。save_template 为真时同时写入新建模板。不写卡片配置。"""
        return editor.apply_rating_schema(
            self._card_model, draft_json, save_template, self._emit_field_error
        )

    @Slot()
    def chooseAvatar(self) -> None:  # noqa: N802
        parent = self.parent()
        editor.choose_avatar(self._card_model, parent if isinstance(parent, QWidget) else None)

    # ---- 文件与撤销：转发为主窗口的信号 ----

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

    # ---- PRTS 与更新 ----

    @Slot(str)
    def requestPrtsQuery(self, enemy_name: str) -> None:  # noqa: N802
        name = prts.query_name(enemy_name)
        if name:
            self.prtsQueryRequested.emit(name)

    @Slot(int)
    def requestPrtsLevelChange(self, level_index: int) -> None:  # noqa: N802
        """请求把当前卡切换到该级别；没有导入上下文或级别不在表内时忽略。"""
        if prts.allows_level_change(self._prts_levels, level_index):
            self.prtsLevelChangeRequested.emit(int(level_index))

    @Slot()
    def requestAbout(self) -> None:  # noqa: N802
        self.aboutRequested.emit()

    @Slot()
    def requestCheckUpdates(self) -> None:  # noqa: N802
        self.checkUpdatesRequested.emit()

    @Slot(str)
    def dismissUpdate(self, tag: str) -> None:  # noqa: N802
        self.dismissUpdateRequested.emit(tag)

    @Slot(bool)
    def setUpdateCheckEnabled(self, enabled: bool) -> None:  # noqa: N802
        app.save_update_check_enabled(enabled)
        self.updateCheckEnabledChanged.emit()

    # ---- AI 评价 ----

    @Slot()
    def requestAiSettings(self) -> None:  # noqa: N802
        self.aiSettingsRequested.emit()

    @Slot(str, result=str)
    def aiBaseUrlPreview(self, base_url: str) -> str:  # noqa: N802
        """该地址最终请求到的完整 URL；只用于显示，不阻止保存。"""
        return ai.base_url_preview(base_url)

    @Slot(str, str, str, result=bool)
    def saveAiSettings(self, base_url: str, model: str, api_key: str) -> bool:  # noqa: N802
        """写入 AI 配置。形状非法或写盘失败时发字段错误并返回 False，界面据此保持打开。"""
        try:
            ai.save_settings(base_url, model, api_key)
        except (ValueError, FileOperationError) as error:
            self._emit_field_error("ai_settings", str(error))
            return False
        self.aiSettingsChanged.emit()
        self.show_toast("AI 配置已保存", "success")
        return True

    @Slot(result=str)
    def aiPersonaText(self) -> str:  # noqa: N802
        """面板打开时预填的人设：偏好里的自定义值，未自定义则为内置默认。"""
        return ai.persona_text()

    @Slot(result=str)
    def aiDefaultPersona(self) -> str:  # noqa: N802
        """内置默认人设，供面板「恢复默认」使用。"""
        return ai.default_persona()

    @Slot(result=str)
    def aiContractText(self) -> str:  # noqa: N802
        """输出契约全文，供面板只读展示；由应用固定生成，界面不提供编辑入口。"""
        return ai.contract_text()

    @Slot(str, result=bool)
    def saveAiPersona(self, persona: str) -> bool:  # noqa: N802
        """人设落盘（与内置默认相同则存空串）；失败 toast 并返回 False。"""
        try:
            ai.save_persona(persona)
        except FileOperationError as error:
            self.show_toast(f"人设保存失败：{error}", "error")
            return False
        return True

    @Slot(str, result=str)
    def aiRequestPreview(self, persona: str) -> str:  # noqa: N802
        """预览组装后实际会发出的两条 message（system、user）；与发请求同源。"""
        return ai.request_preview(self._card_model, persona)

    @Slot(str)
    def requestAiReview(self, persona: str) -> None:  # noqa: N802
        """按面板里的人设发起一次评价：未配置则打开设置框、忙则忽略、基准缺失则报错。"""
        if self._ai_busy:
            self.show_toast("正在生成评价，请稍候", "info")
            return
        config = ai.request_config()
        if config is None:
            self.aiSettingsRequested.emit()
            return
        try:
            baseline = ai.load_review_baseline()
        except FileOperationError as error:
            self.show_dialog("基准数据不可用", ai.baseline_error_hint(error), "error")
            return
        snapshot, revision, text = ai.begin_review(self._card_model, persona, self._session)
        self.aiReviewRequested.emit(config, text, snapshot, baseline, revision)

    @Slot(str, result=bool)
    def applyAiComment(self, text: str) -> bool:  # noqa: N802
        """采纳简评：数据自请求以来未变则直接写入并返回 True；已变则请求二次确认。"""
        decision = ai.comment_decision(self._card_model, text, self._session)
        if decision == "empty":
            return False
        if decision == "confirm":
            self.aiCommentConfirmRequested.emit(text.strip())
            return False
        ai.write_comment(self._card_model, text)
        self.show_toast("已写入简评，可 Ctrl+Z 撤销", "success")
        return True

    @Slot(str)
    def applyAiCommentConfirmed(self, text: str) -> None:  # noqa: N802
        """二次确认后写入（请求之后卡片数据已被改动）。"""
        if not text.strip():
            return
        ai.write_comment(self._card_model, text)
        self.show_toast("已写入简评，可 Ctrl+Z 撤销", "success")

    @Slot()
    def abandonAiReview(self) -> None:  # noqa: N802
        """请求途中关闭弹窗：本次结果作废，并请主窗口取消在飞请求。"""
        self.invalidate_ai_review()
        self.aiAbandonRequested.emit()

    # ---- 主窗口调用（非 QML 可见）----

    def set_update_banner(self, tag: str, url: str) -> None:
        """把是否显示横幅的结果交给界面。标签为空则不显示。"""
        if tag == self._update_banner_tag and url == self._update_banner_url:
            return
        self._update_banner_tag = tag
        self._update_banner_url = url
        self.updateBannerChanged.emit()

    def set_card_model(self, card_model: CardModel) -> None:
        """在新建卡片后切换数据源，避免 QML 持有过期模型。"""
        self._link.attach(card_model)
        self._card_model = card_model
        self._skills.set_card_model(card_model)
        self.invalidate_ai_review()
        self._publish_model()
        self.undoStateChanged.emit()

    def set_prts_busy(self, busy: bool) -> None:
        """PRTS 拉取在飞；由主窗口在起线程与线程结束时调用。"""
        if self._prts_busy != busy:
            self._prts_busy = busy
            self.prtsBusyChanged.emit(busy)

    def set_prts_levels(self, levels: list[dict]) -> None:
        """主窗口在导入成功后同步级别列表；传空表即清除（当前级别由卡片模型提供）。"""
        self._prts_levels = [dict(item) for item in levels]
        self.prtsLevelsChanged.emit()

    def set_ai_busy(self, busy: bool) -> None:
        """由主窗口在起线程与线程结束时调用。"""
        if busy == self._ai_busy:
            return
        self._ai_busy = busy
        self.aiBusyChanged.emit()

    def invalidate_ai_review(self) -> None:
        """换卡或换数据后调用：在飞评价按世代号作废，已展示的预览一并失效。"""
        self._session.invalidate()

    def ai_evaluation_finished(self, result: AiEvaluationResult, revision: int) -> None:
        """线程结果回主线程：世代号不符即作废并提示，不弹窗、不写入。"""
        if not ai.accept_result(result, revision, self._session):
            self.show_toast("本次评价结果已作废", "warning")
            return
        self.aiCommentReady.emit()

    def ai_evaluation_failed(self, error: Exception, revision: int) -> None:
        """线程异常回主线程：按异常子类出文案；过时失败静默丢弃。"""
        if not self._session.accepts(revision):
            return
        title, message = ai.error_message(error)
        self.show_dialog(title, message, "error")

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
        self.removeRecentConfirmRequested.emit(*files.recent_confirm_args(path))

    # ---- 内部 ----

    def _emit_field_error(self, field: str, message: str) -> None:
        self.fieldError.emit(field, message)

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

    def _on_card_ready(self, result: object, _revision: int) -> None:
        if isinstance(result, QPixmap):
            self._image_provider.set_pixmap(result)
            self._preview_revision += 1
            self.previewChanged.emit(self._preview_revision)
