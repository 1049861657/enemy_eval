"""Qt Quick 主窗口：保留业务编排，所有编辑与预览交给 QML 工作区。"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QCloseEvent
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox, QStatusBar

from core.optimization import get_resource_manager
from utils import (
    AdaptiveDebouncer,
    EnemyEvalException,
    PrtsFetchThread,
    categorize_error_message,
    current_render_options,
    error_handler,
    get_app_build_time,
    get_app_version,
)

from .card_model import CardModel
from .constants import (
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_DEFAULT_X,
    WINDOW_DEFAULT_Y,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from .qml_bridge import CardImageProvider, QmlBridge
from .render_coordinator import RenderCoordinator

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主窗口仅负责文件、PRTS、生命周期和渲染调度。"""

    def __init__(self) -> None:
        super().__init__()
        self.card_model = CardModel(self)
        self.prts_fetch_thread: PrtsFetchThread | None = None
        self._render = RenderCoordinator(self)
        self._debouncer = AdaptiveDebouncer(min_delay=200, max_delay=520)
        self._app_version = get_app_version()
        self._app_build_time = get_app_build_time()
        self.setWindowTitle(f"敌人评价卡片实时编辑器 v{self._app_version}")
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
        self._bridge.saveRequested.connect(self._save_config)
        self._bridge.exportRequested.connect(self._export_image)
        self._bridge.refreshRequested.connect(self._generate_card)
        self._bridge.quitRequested.connect(self.close)
        self._bridge.prtsQueryRequested.connect(self._fetch_prts_data)
        self._bridge.aboutRequested.connect(self._show_about)

    def _connect_model_signals(self) -> None:
        self.card_model.dataChanged.connect(self._on_data_changed)

    def _on_data_changed(self) -> None:
        self._debouncer.debounce(self._generate_card)

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

    def _new_card(self) -> None:
        previous_model = self.card_model
        previous_model.dataChanged.disconnect(self._on_data_changed)
        self.card_model = CardModel(self)
        self._bridge.set_card_model(self.card_model)
        self._connect_model_signals()
        previous_model.deleteLater()
        self._generate_card()

    def _open_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开配置文件", "", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if not file_path:
            return
        try:
            with error_handler("加载配置文件"):
                self.card_model.load_from_file(file_path)
                self.status_bar.showMessage(f"已加载：{Path(file_path).name}")
                self._generate_card()
        except EnemyEvalException as error:
            title, message = categorize_error_message(str(error))
            self._bridge.show_dialog(title, message, "warning")

    def _save_config(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存配置文件",
            f"{self.card_model.enemy_data.name}_config.json",
            "JSON 文件 (*.json);;所有文件 (*)",
        )
        if not file_path:
            return
        try:
            with error_handler("保存配置文件"):
                self.card_model.save_to_file(file_path)
                self.status_bar.showMessage(f"已保存：{Path(file_path).name}")
        except EnemyEvalException as error:
            title, message = categorize_error_message(str(error))
            self._bridge.show_dialog(title, message, "warning")

    def _export_image(self) -> None:
        if self._render.last_generated_pixmap is None:
            self._bridge.show_toast("请先生成卡片预览")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出图片",
            f"{self.card_model.enemy_data.name}.png",
            "PNG 图片 (*.png);;JPG 图片 (*.jpg);;所有文件 (*)",
        )
        if not file_path:
            return
        error = self._render.save_current(file_path)
        if error is None:
            self.status_bar.showMessage(f"已导出：{Path(file_path).name}")
            self._bridge.show_toast(f"已导出：{file_path}")
        else:
            title, message = categorize_error_message(error)
            self._bridge.show_dialog(title, message, "error")

    def _show_about(self) -> None:
        build_time = (
            f"\n构建日期：{self._app_build_time}" if self._app_build_time else ""
        )
        self._bridge.show_dialog(
            "关于",
            "敌人评价卡片实时编辑器\n\n"
            f"版本：{self._app_version}"
            f"{build_time}\n\n"
            "一个现代化的敌人评价卡片生成工具\n"
            "支持实时预览和属性编辑\n\n"
            "技术栈：Python 3.13 + PySide6 + Qt Quick + Skia-Python",
            "info",
        )

    def _fetch_prts_data(self, enemy_name: str) -> None:
        if self.prts_fetch_thread is not None and self.prts_fetch_thread.isRunning():
            self._bridge.show_toast("正在获取 PRTS 数据，请稍候")
            return
        self.status_bar.showMessage(f"正在从 PRTS 获取「{enemy_name}」的数据…")
        self._bridge.set_prts_busy(True)
        thread = PrtsFetchThread(enemy_name)
        thread.fetchFinished.connect(
            lambda enemy_data, error_msg, name=enemy_name: self._on_prts_fetch_finished(
                name, enemy_data, error_msg
            )
        )
        thread.finished.connect(lambda thread_ref=thread: self._on_prts_thread_finished(thread_ref))
        self.prts_fetch_thread = thread
        thread.start()

    def _on_prts_fetch_finished(self, enemy_name: str, enemy_data, error_msg) -> None:
        self._bridge.set_prts_busy(False)
        if enemy_data is not None:
            self.card_model.set_enemy_data(enemy_data)
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
                self._debouncer.cleanup()
                get_resource_manager().clear_caches()
        except Exception:
            logger.exception("窗口资源清理失败")
        event.accept()
