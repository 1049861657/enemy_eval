"""Qt Quick 主窗口：保留业务编排，所有编辑与预览交给 QML 工作区。"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QCloseEvent
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox, QStatusBar

from core.render.avatar_prefetch import is_avatar_cached
from core.render.canvas_pool import clear_caches
from models import EnemyData
from models.media import is_url
from utils.app.ai_prefs import AiRequestConfig
from utils.app.render_prefs import current_render_options
from utils.app.settings import (
    AppSettings,
    clear_recent_files,
    load_app_settings,
    remember_recent_file,
    remove_recent_file,
)
from utils.app.update_prefs import (
    clear_update_seen,
    mark_update_checked,
    set_update_block_until,
    set_update_seen,
    set_update_skip_tag,
)
from utils.app.version import get_app_version
from utils.app.update_check import is_newer
from utils.qt.debounce import AdaptiveDebouncer
from utils.errors import (
    EnemyEvalException,
    categorize_error_message,
    error_handler,
)
from utils.fs.filenames import safe_filename
from utils.prts.enemy_builder import rebuild_enemy_data
from utils.prts.field_mapping import build_enemy_raw
from utils.qt.ai_task import AiEvaluateThread
from utils.qt.avatar_task import NetworkAvatarPrefetchThread
from utils.qt.prts_task import PrtsFetchThread
from utils.qt.update_task import UpdateCheckThread

from .bridge.preview import CardImageProvider
from .card_model import NO_PRTS_LEVEL, CardModel
from .qml_bridge import QmlBridge
from .render_coordinator import RenderCoordinator

logger = logging.getLogger(__name__)

# 主窗口几何：首次启动的位置与尺寸，以及用户可拖到的最小尺寸。
WINDOW_DEFAULT_X = 100
WINDOW_DEFAULT_Y = 100
WINDOW_DEFAULT_WIDTH = 1400
WINDOW_DEFAULT_HEIGHT = 900
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800

_UPDATE_CHECK_COOLDOWN_S = 24 * 60 * 60
_UPDATE_CHECK_BACKOFF_S = 30 * 60


class MainWindow(QMainWindow):
    """主窗口仅负责文件、PRTS、生命周期和渲染调度。"""

    def __init__(self) -> None:
        super().__init__()
        self.card_model = CardModel(self)
        self.prts_fetch_thread: PrtsFetchThread | None = None
        self.avatar_prefetch_thread: NetworkAvatarPrefetchThread | None = None
        self.update_check_thread: UpdateCheckThread | None = None
        self.ai_evaluate_thread: AiEvaluateThread | None = None
        self._update_check_manual = False
        self._prts_context: dict[str, Any] | None = None
        self._render = RenderCoordinator(self)
        self._debouncer = AdaptiveDebouncer(min_delay=200, max_delay=520)
        self._app_version = get_app_version()
        self.setWindowTitle(QApplication.applicationDisplayName())
        self.setGeometry(
            WINDOW_DEFAULT_X,
            WINDOW_DEFAULT_Y,
            WINDOW_DEFAULT_WIDTH,
            WINDOW_DEFAULT_HEIGHT,
        )
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        if not self._create_central_widget():
            return
        self._create_status_bar()
        self._connect_signals()
        self._generate_card()
        QTimer.singleShot(3000, self, self._maybe_check_updates)

    def _create_central_widget(self) -> bool:
        self._image_provider = CardImageProvider()
        self._bridge = QmlBridge(
            self.card_model, self._render, self._image_provider, parent=self
        )
        self.workspace = QQuickWidget(self)
        self.workspace.setResizeMode(
            QQuickWidget.ResizeMode.SizeRootObjectToView
        )
        self.workspace.engine().addImageProvider("enemy-card", self._image_provider)
        self.workspace.setInitialProperties({"controller": self._bridge})
        self.workspace.setSource(
            QUrl.fromLocalFile(str(Path(__file__).with_name("qml") / "Workspace.qml"))
        )
        if self.workspace.status() == QQuickWidget.Status.Error:
            details = "\n".join(
                error.toString() for error in self.workspace.errors()
            ) or "未知 QML 错误"
            logger.error("QML 加载失败：%s", details)
            self.workspace.hide()
            QMessageBox.critical(
                self,
                "界面加载失败",
                f"无法加载编辑器界面：\n\n{details}",
            )
            QTimer.singleShot(0, QApplication.quit)
            return False
        self.setCentralWidget(self.workspace)
        return True

    def _create_status_bar(self) -> None:
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _connect_signals(self) -> None:
        self._connect_model_signals()
        self._render.cardReady.connect(self._on_card_ready)
        self._render.renderFailed.connect(self._on_render_failed)
        self._render.busyChanged.connect(self._on_render_busy)
        self._bridge.newRequested.connect(self._new_card)
        self._bridge.openRequested.connect(self._open_file)
        self._bridge.openRecentRequested.connect(self._open_file)
        self._bridge.removeRecentRequested.connect(self._remove_recent)
        self._bridge.clearRecentRequested.connect(self._clear_recent)
        self._bridge.saveRequested.connect(self._save_config)
        self._bridge.exportRequested.connect(self._export_image)
        self._bridge.refreshRequested.connect(self._generate_card)
        self._bridge.quitRequested.connect(self.close)
        self._bridge.prtsQueryRequested.connect(self._fetch_prts_data)
        self._bridge.prtsLevelChangeRequested.connect(self._change_prts_level)
        self._bridge.checkUpdatesRequested.connect(self._check_updates_manually)
        self._bridge.dismissUpdateRequested.connect(self._dismiss_update)
        self._bridge.aiReviewRequested.connect(self._start_ai_review)
        self._bridge.aiAbandonRequested.connect(self._abandon_ai_review)

    def _connect_model_signals(self) -> None:
        self.card_model.dataChanged.connect(self._on_data_changed)
        self.card_model.avatarPathChanged.connect(self._ensure_avatar_cached)

    def _on_data_changed(self) -> None:
        self._debouncer.debounce(self._generate_card)

    def _ensure_avatar_cached(self, avatar_path: str) -> None:
        """网络头像不进渲染线程下载：先在后台补进图像缓存，再重绘一次。

        PRTS 拉取路径已在拉取线程里预取，这里命中缓存后直接返回。
        """
        if not is_url(avatar_path) or is_avatar_cached(avatar_path):
            return
        running = self.avatar_prefetch_thread
        if running is not None and running.isRunning():
            running.requestInterruption()
        thread = NetworkAvatarPrefetchThread(avatar_path)
        thread.prefetchFinished.connect(
            lambda ok, url=avatar_path: self._on_avatar_prefetched(ok, url)
        )
        thread.finished.connect(lambda t=thread: self._on_avatar_thread_finished(t))
        self.avatar_prefetch_thread = thread
        thread.start()

    def _on_avatar_prefetched(self, ok: bool, avatar_path: str) -> None:
        if not ok:
            return
        if avatar_path != (self.card_model.enemy_data.avatar_path or ""):
            return  # 预取期间头像已改，等新线程的结果
        self._generate_card()

    def _on_avatar_thread_finished(self, thread: NetworkAvatarPrefetchThread) -> None:
        thread.deleteLater()
        if self.avatar_prefetch_thread is thread:
            self.avatar_prefetch_thread = None

    def _generate_card(self) -> None:
        self._render.request(self.card_model.enemy_data, current_render_options())

    def _on_card_ready(self, _result: object, _revision: int) -> None:
        self.status_bar.showMessage("卡片预览已更新")

    def _on_render_failed(self, error_message: str) -> None:
        self.status_bar.showMessage("生成失败")
        title, message = categorize_error_message(error_message)
        self._bridge.show_dialog(title, message, "error")
        logger.error("卡片生成失败：%s", error_message)

    def _on_render_busy(self, busy: bool) -> None:
        if busy:
            self.status_bar.showMessage("正在生成卡片…")

    def _warn_missing_avatar(self) -> None:
        """本地头像文件不存在时提示一次；不阻断加载。"""
        avatar_path = self.card_model.enemy_data.avatar_path or ""
        if not avatar_path or is_url(avatar_path) or Path(avatar_path).exists():
            return
        self._bridge.show_toast("头像文件不存在，已按无头像显示", "warning")

    def _new_card(self) -> None:
        previous_model = self.card_model
        previous_model.dataChanged.disconnect(self._on_data_changed)
        self.card_model = CardModel(self)
        self._bridge.set_card_model(self.card_model)
        self._connect_model_signals()
        previous_model.deleteLater()
        self._clear_prts_context()
        self._generate_card()

    def _open_file(self, path: str | None = None) -> None:
        """打开配置；带路径时直接打开（最近打开列表）。文件已不存在时改为询问是否移除该记录，不弹报错。"""
        from_recent = path is not None
        file_path = path
        if file_path is None:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "打开配置文件", "", "JSON 文件 (*.json);;所有文件 (*)"
            )
        if not file_path:
            return
        try:
            with error_handler("加载配置文件"):
                self.card_model.load_from_file(file_path)
                self._bridge.invalidate_ai_review()
                self._warn_missing_avatar()
                self._clear_prts_context()
                self.status_bar.showMessage(f"已加载：{Path(file_path).name}")
                self._generate_card()
                remember_recent_file(file_path)
                self._bridge.refresh_recent_files()
        except EnemyEvalException as error:
            self._bridge.refresh_recent_files()
            if from_recent and not Path(file_path).exists():
                self._bridge.confirm_remove_recent(file_path)
                return
            title, message = categorize_error_message(str(error))
            self._bridge.show_dialog(title, message, "warning")

    def _save_config(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存配置文件",
            f"{safe_filename(self.card_model.enemy_data.name)}_config.json",
            "JSON 文件 (*.json);;所有文件 (*)",
        )
        if not file_path:
            return
        try:
            with error_handler("保存配置文件"):
                self.card_model.save_to_file(file_path)
                self.status_bar.showMessage(f"已保存：{Path(file_path).name}")
                remember_recent_file(file_path)
                self._bridge.refresh_recent_files()
        except EnemyEvalException as error:
            title, message = categorize_error_message(str(error))
            self._bridge.show_dialog(title, message, "warning")

    def _remove_recent(self, path: str) -> None:
        remove_recent_file(path)
        self._bridge.refresh_recent_files()

    def _clear_recent(self) -> None:
        clear_recent_files()
        self._bridge.refresh_recent_files()

    def _export_image(self) -> None:
        if self._render.last_generated_pixmap is None:
            self._bridge.show_toast("请先生成卡片预览", "info")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出图片",
            f"{safe_filename(self.card_model.enemy_data.name)}.png",
            "PNG 图片 (*.png);;JPG 图片 (*.jpg);;所有文件 (*)",
        )
        if not file_path:
            return
        error = self._render.save_current(file_path)
        if error is None:
            self.status_bar.showMessage(f"已导出：{Path(file_path).name}")
            self._bridge.show_toast(f"已导出：{file_path}", "success")
        else:
            title, message = categorize_error_message(error)
            self._bridge.show_dialog(title, message, "error")

    def _maybe_check_updates(self) -> None:
        self._sync_update_banner()
        settings = load_app_settings()
        if self._update_check_due(settings, time.time()):
            self._start_update_check(manual=False)

    def _check_updates_manually(self) -> None:
        self._start_update_check(manual=True)

    def _update_check_due(self, settings: AppSettings, now: float) -> bool:
        if not settings.update_check_enabled:
            return False
        if now < settings.update_check_block_until:
            return False
        last = settings.update_check_last_ts
        if last > now:
            return True
        return last == 0 or now - last >= _UPDATE_CHECK_COOLDOWN_S

    def _start_update_check(self, *, manual: bool) -> None:
        running = self.update_check_thread
        if running is not None and running.isRunning():
            if manual:
                self._update_check_manual = True
                self._bridge.show_toast("正在检查更新", "info")
            return
        self._update_check_manual = manual
        thread = UpdateCheckThread(load_app_settings().update_check_etag)
        thread.checkFinished.connect(self._on_update_check_finished)
        thread.finished.connect(
            lambda thread_ref=thread: self._on_update_check_thread_finished(thread_ref)
        )
        self.update_check_thread = thread
        thread.start()

    def _on_update_check_finished(
        self, outcome: str, tag: str, url: str, etag: str, retry_at: float
    ) -> None:
        manual = self._update_check_manual
        now = time.time()
        if outcome in ("update", "current"):
            set_update_seen(tag, url, etag)
            mark_update_checked(now)
        elif outcome == "unchanged":
            settings = load_app_settings()
            if settings.update_check_etag and not settings.update_seen_tag:
                clear_update_seen()
            mark_update_checked(now)
        elif outcome == "none":
            clear_update_seen()
            mark_update_checked(now)
        elif outcome == "error":
            set_update_block_until(self._update_block_until(now, retry_at))
        self._sync_update_banner()
        if not manual:
            return
        if outcome == "error":
            self._bridge.show_toast("暂时无法检查更新", "warning")
            return
        if not self._bridge.updateBannerTag:
            self._bridge.show_toast("已是最新版本", "success")

    def _update_block_until(self, now: float, retry_at: float) -> float:
        until = retry_at if retry_at > now else now + _UPDATE_CHECK_BACKOFF_S
        return min(until, now + _UPDATE_CHECK_COOLDOWN_S)

    def _sync_update_banner(self) -> None:
        settings = load_app_settings()
        tag = settings.update_seen_tag
        show = bool(tag) and tag != settings.update_check_skip_tag and is_newer(
            self._app_version, tag
        )
        self._bridge.set_update_banner(
            tag if show else "",
            settings.update_seen_url if show else "",
        )

    def _dismiss_update(self, tag: str) -> None:
        set_update_skip_tag(tag)
        self._sync_update_banner()

    def _on_update_check_thread_finished(self, thread: UpdateCheckThread) -> None:
        thread.deleteLater()
        if self.update_check_thread is thread:
            self.update_check_thread = None

    def _fetch_prts_data(self, enemy_name: str) -> None:
        if self.prts_fetch_thread is not None and self.prts_fetch_thread.isRunning():
            self._bridge.show_toast("正在获取 PRTS 数据，请稍候", "info")
            return
        self.status_bar.showMessage(f"正在从 PRTS 获取「{enemy_name}」的数据…")
        self._bridge.set_prts_busy(True)
        thread = PrtsFetchThread(enemy_name)
        thread.fetchFinished.connect(
            lambda enemy_data, error_msg, context, name=enemy_name: self._on_prts_fetch_finished(
                name, enemy_data, error_msg, context
            )
        )
        thread.finished.connect(lambda thread_ref=thread: self._on_prts_thread_finished(thread_ref))
        self.prts_fetch_thread = thread
        thread.start()

    def _on_prts_fetch_finished(
        self, enemy_name: str, enemy_data, error_msg, context: dict[str, Any] | None
    ) -> None:
        self._bridge.set_prts_busy(False)
        if enemy_data is not None:
            self.card_model.set_enemy_data(enemy_data)
            self._bridge.invalidate_ai_review()
            self._apply_prts_context(context)
            self.status_bar.showMessage(f"已成功导入「{enemy_name}」的 PRTS 数据")
            self._generate_card()
            return
        error_msg = error_msg or "未知错误"
        if "未找到敌人" in error_msg:
            self._bridge.show_dialog("未找到敌人", error_msg, "warning")
        else:
            self._bridge.show_dialog("获取失败", error_msg, "error")
        self.status_bar.showMessage("获取 PRTS 数据失败")

    def _on_prts_thread_finished(self, thread: PrtsFetchThread) -> None:
        thread.deleteLater()
        if self.prts_fetch_thread is thread:
            self.prts_fetch_thread = None

    def _start_ai_review(
        self,
        config: AiRequestConfig,
        persona: str,
        snapshot: EnemyData,
        baseline: dict[str, Any],
        revision: int,
    ) -> None:
        """起一次评价请求；忙态与状态栏文案同 PRTS 路径，结果按世代号收口。"""
        running = self.ai_evaluate_thread
        if running is not None and running.isRunning():
            self._bridge.show_toast("正在生成评价，请稍候", "info")
            return
        self._bridge.set_ai_busy(True)
        self.status_bar.showMessage(f"正在生成 AI 评价（{config.model}）…")
        thread = AiEvaluateThread(config, persona, baseline, snapshot, revision)
        thread.evaluationFinished.connect(self._bridge.ai_evaluation_finished)
        thread.evaluationFailed.connect(self._bridge.ai_evaluation_failed)
        thread.finished.connect(lambda ref=thread: self._on_ai_thread_finished(ref))
        self.ai_evaluate_thread = thread
        thread.start()

    def _on_ai_thread_finished(self, thread: AiEvaluateThread) -> None:
        thread.deleteLater()
        if self.ai_evaluate_thread is thread:
            self.ai_evaluate_thread = None
            self._bridge.set_ai_busy(False)
            self.status_bar.showMessage("就绪")

    def _abandon_ai_review(self) -> None:
        """取消在飞的评价请求；线程在轮询点结束，忙态由 finished 收尾。"""
        thread = self.ai_evaluate_thread
        if thread is not None and thread.isRunning():
            thread.requestInterruption()

    def _apply_prts_context(self, context: dict[str, Any] | None) -> None:
        """记住本次导入的页面上下文，并把级别来源交给卡片模型（随撤销栈快照回放）。"""
        source = context if isinstance(context, dict) else None
        if source is None:
            self._clear_prts_context()
            return
        levels = list(source.get("levels") or [])
        self._prts_context = {
            "name": str(source.get("name") or ""),
            "wikitext": str(source.get("wikitext") or ""),
            "levels": levels,
        }
        self._bridge.set_prts_levels(levels)
        self.card_model.set_prts_level_index(
            int(source.get("level_index", NO_PRTS_LEVEL)) if levels else NO_PRTS_LEVEL
        )

    def _clear_prts_context(self) -> None:
        """换卡后本次导入的级别上下文失效，级别切换入口随之消失。"""
        self._prts_context = None
        self._bridge.set_prts_levels([])

    def _change_prts_level(self, level_index: int) -> None:
        """把当前卡切换到所选级别：只覆盖 PRTS 来源字段，保留作者填写的简评 / 评分 / 等级 / 头像。"""
        context = self._prts_context
        if not context or level_index == self.card_model.prts_level_index:
            return
        levels = list(context.get("levels") or [])
        label = next(
            (str(item.get("label")) for item in levels if item.get("index") == level_index),
            f"级别{level_index}",
        )
        current = self.card_model.enemy_data
        raw = build_enemy_raw(str(context.get("wikitext") or ""), level_index)
        rebuilt = (
            None
            if raw is None
            else rebuild_enemy_data(raw, str(context.get("name") or current.name), current)
        )
        if rebuilt is None:
            self._bridge.show_dialog(
                "切换级别失败", "未能从页面数据中解析出该级别的数值。", "error"
            )
            return
        self.card_model.apply_enemy_data(rebuilt, level_index)
        self._bridge.invalidate_ai_review()
        self.status_bar.showMessage(f"已切换到{label}")
        self._generate_card()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        try:
            with error_handler("清理资源", silent=True):
                self._render.cleanup()
                thread = self.prts_fetch_thread
                if thread is not None and thread.isRunning():
                    thread.requestInterruption()
                    if not thread.wait(3000):
                        logger.error(
                            "PRTS 拉取线程未能在 3 秒内停止，放弃等待且不 terminate"
                        )
                prefetch_thread = self.avatar_prefetch_thread
                if prefetch_thread is not None and prefetch_thread.isRunning():
                    prefetch_thread.requestInterruption()
                    if not prefetch_thread.wait(3000):
                        logger.error(
                            "头像预取线程未能在 3 秒内停止，放弃等待且不 terminate"
                        )
                update_thread = self.update_check_thread
                if update_thread is not None and update_thread.isRunning():
                    update_thread.requestInterruption()
                    if not update_thread.wait(3000):
                        logger.error(
                            "版本检查线程未能在 3 秒内停止，放弃等待且不 terminate"
                        )
                ai_thread = self.ai_evaluate_thread
                if ai_thread is not None and ai_thread.isRunning():
                    ai_thread.requestInterruption()
                    if not ai_thread.wait(3000):
                        logger.error(
                            "AI 评价线程未能在 3 秒内停止，放弃等待且不 terminate"
                        )
                self._debouncer.cleanup()
                clear_caches()
        except Exception:
            logger.exception("窗口资源清理失败")
        event.accept()
