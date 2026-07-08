"""
主窗口 - 敌人评价卡片实时编辑器主界面
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QSplitter, QStatusBar, QFileDialog,
                               QMessageBox, QProgressBar)

from utils import (
    AdaptiveDebouncer,
    EnemyEvalException,
    PrtsFetchThread,
    categorize_error_message,
    error_handler,
    get_app_version,
)
from .render_coordinator import RenderCoordinator
from .card_model import CardModel
from .constants import (
    WINDOW_DEFAULT_X, WINDOW_DEFAULT_Y, WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    SPLITTER_LEFT_WIDTH, SPLITTER_RIGHT_WIDTH,
)
from .preview_widget import PreviewWidget
from .property_panel import PropertyPanel
from .prts_reference_dialog import PrtsReferenceDialog

# 设置日志
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主窗口类 - 专注于UI管理和用户交互"""
    
    def __init__(self):
        super().__init__()
        self.card_model = CardModel(self)
        self.prts_fetch_thread = None
        self._render = RenderCoordinator(self)
        self._debouncer = AdaptiveDebouncer(min_delay=200, max_delay=520)
        self._app_version = get_app_version()
        self.setWindowTitle(f"敌人评价卡片实时编辑器 v{self._app_version}")
        self.setGeometry(WINDOW_DEFAULT_X, WINDOW_DEFAULT_Y, WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # 设置样式
        self._load_styles()
        
        # 创建UI
        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()
        
        # 连接信号
        self._connect_signals()
        
        # 初始生成一次卡片
        self._generate_card()
        
    def _load_styles(self):
        """加载样式文件"""
        from utils import resource_manager
        
        style_path = Path(__file__).parent / "styles.qss"
        if style_path.exists():
            with open(style_path, 'r', encoding='utf-8') as f:
                styles = resource_manager.get_qss_with_resources(f.read())
                self.setStyleSheet(styles)
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 新建
        new_action = QAction("新建", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_card)
        file_menu.addAction(new_action)
        
        # 打开
        open_action = QAction("打开", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)
        
        # 保存
        save_action = QAction("保存配置", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_config)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        # 导出图片
        export_action = QAction("导出图片", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export_image)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        # 参考PRTS
        prts_action = QAction("参考PRTS", self)
        prts_action.triggered.connect(self._reference_prts)
        edit_menu.addAction(prts_action)
        
        edit_menu.addSeparator()
        
        # 重置
        reset_action = QAction("重置数据", self)
        reset_action.triggered.connect(self._reset_data)
        edit_menu.addAction(reset_action)
        
        # 预览菜单
        preview_menu = menubar.addMenu("预览")
        
        # 刷新预览
        refresh_action = QAction("刷新预览", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self._generate_card)
        preview_menu.addAction(refresh_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        # 关于
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_central_widget(self):
        """创建中央部件"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧属性编辑面板
        self.property_panel = PropertyPanel(self.card_model)
        splitter.addWidget(self.property_panel)
        
        # 右侧预览组件
        self.preview_widget = PreviewWidget()
        splitter.addWidget(self.preview_widget)
        
        # 设置分割器比例 (30% : 70%)
        splitter.setSizes([SPLITTER_LEFT_WIDTH, SPLITTER_RIGHT_WIDTH])
        splitter.setStretchFactor(0, 0)  # 左侧不拉伸
        splitter.setStretchFactor(1, 1)  # 右侧可拉伸
        
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        self.status_bar.showMessage("就绪")
    
    def _connect_signals(self):
        """连接信号与槽（一次性，仅在 __init__ 中调用）"""
        self._connect_model_signals()
        self.preview_widget.exportRequested.connect(self._export_image)
        self._render.cardReady.connect(self._on_card_ready)
        self._render.renderFailed.connect(self._on_render_failed)
        self._render.busyChanged.connect(self._on_render_busy)

    def _connect_model_signals(self):
        """连接当前 card_model 的信号，可在 card_model 被替换后重复调用"""
        self.card_model.dataChanged.connect(self._on_data_changed)

    def _on_data_changed(self):
        self._debouncer.debounce(self._generate_card)

    def _generate_card(self):
        self._render.request(self.card_model.enemy_data)

    def _on_card_ready(self, result: object, _revision: int) -> None:
        """RenderCoordinator.cardReady → 更新预览和状态栏。"""
        if isinstance(result, str):
            self.preview_widget.load_image(result)
            self.status_bar.showMessage(f"卡片已生成: {Path(result).name}")
        else:
            self.preview_widget.load_pixmap(result)
            self.status_bar.showMessage("卡片预览已更新")

    def _on_render_failed(self, error_message: str) -> None:
        """RenderCoordinator.renderFailed → 显示错误提示。"""
        self.status_bar.showMessage("生成失败")
        title, message = categorize_error_message(error_message)
        QMessageBox.critical(self, title, message)

    def _on_render_busy(self, busy: bool) -> None:
        """RenderCoordinator.busyChanged → 进度条开关。"""
        self.progress_bar.setVisible(busy)
        if busy:
            self.status_bar.showMessage("正在生成卡片...")
            self.progress_bar.setRange(0, 0)

    
    def _new_card(self):
        """新建卡片"""
        reply = QMessageBox.question(self, "新建卡片", "是否要丢弃当前数据并创建新卡片？")
        if reply == QMessageBox.StandardButton.Yes:
            self.card_model = CardModel(self)
            self.property_panel.set_card_model(self.card_model)
            self._connect_model_signals()
            self._generate_card()
    
    def _open_file(self):
        """打开配置文件 - 增强错误处理"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开配置文件", "", "JSON文件 (*.json);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with error_handler("加载配置文件"):
                    self.card_model.load_from_file(file_path)
                    self.property_panel.refresh_from_model()
                    self.status_bar.showMessage(f"已加载: {Path(file_path).name}")
                    self._generate_card()  # 自动刷新预览
            except EnemyEvalException as e:
                title, message = categorize_error_message(str(e))
                QMessageBox.warning(self, title, message)
    
    def _save_config(self):
        """保存配置文件 - 增强错误处理"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存配置文件", f"{self.card_model.enemy_data.name}_config.json", 
            "JSON文件 (*.json);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with error_handler("保存配置文件"):
                    self.card_model.save_to_file(file_path)
                    self.status_bar.showMessage(f"已保存: {Path(file_path).name}")
            except EnemyEvalException as e:
                title, message = categorize_error_message(str(e))
                QMessageBox.warning(self, title, message)
    
    def _export_image(self):
        """导出图片 - 增强错误处理"""
        if self._render.last_generated_pixmap is None:
            QMessageBox.information(self, "提示", "请先生成卡片。")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出图片",
            f"{self.card_model.enemy_data.name}_{self.card_model.enemy_data.grade}.png",
            "PNG图片 (*.png);;JPG图片 (*.jpg);;所有文件 (*)",
        )
        if file_path:
            ok = self._render.save_current(file_path)
            if ok:
                self.status_bar.showMessage(f"已导出: {Path(file_path).name}")
                QMessageBox.information(self, "导出成功", f"图片已保存到:\n{file_path}")
            else:
                QMessageBox.critical(self, "导出失败", "图片保存失败，请检查路径和权限。")
    
    def _reset_data(self):
        """重置数据"""
        reply = QMessageBox.question(self, "重置数据", "是否要重置所有数据到默认值？")
        if reply == QMessageBox.StandardButton.Yes:
            self._new_card()
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            f"敌人评价卡片实时编辑器 v{self._app_version}\n\n"
            "一个现代化的敌人评价卡片生成工具\n"
            "支持实时预览和属性编辑\n\n"
            "技术栈: Python 3.12 + PySide6 + Skia-Python"
        )
    
    def _reference_prts(self):
        """参考PRTS功能 - 输入敌人名称获取数据"""
        if self.prts_fetch_thread is not None and self.prts_fetch_thread.isRunning():
            QMessageBox.information(self, "请稍候", "已有一个PRTS数据请求正在进行中，请等待其完成。")
            return

        enemy_name, ok = PrtsReferenceDialog.get_enemy_name_input(self,"PRTS参考")

        if ok and enemy_name:
            self._fetch_prts_data(enemy_name)

    def _fetch_prts_data(self, enemy_name: str):
        """异步获取PRTS数据并填充到当前模型：起后台线程，不阻塞主线程/事件循环。"""
        self.status_bar.showMessage(f"正在从PRTS获取「{enemy_name}」的数据...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        thread = PrtsFetchThread(enemy_name)
        thread.fetchFinished.connect(
            lambda enemy_data, error_msg, name=enemy_name: self._on_prts_fetch_finished(
                name, enemy_data, error_msg
            )
        )
        thread.finished.connect(lambda thr=thread: self._on_prts_thread_finished(thr))
        self.prts_fetch_thread = thread
        thread.start()

    def _on_prts_fetch_finished(self, enemy_name: str, enemy_data, error_msg):
        """PrtsFetchThread 结果回调：更新模型/提示，不在此处清理线程引用（由 finished 信号统一处理）。"""
        self.progress_bar.setVisible(False)
        if enemy_data is not None:
            self.card_model.set_enemy_data(enemy_data)
            self.property_panel.refresh_from_model()
            self.status_bar.showMessage(f"已成功导入「{enemy_name}」的PRTS数据")
            self._generate_card()  # 刷新预览
        else:
            error_msg = error_msg or "未知错误"
            if "未找到敌人" in error_msg:
                QMessageBox.warning(self, "未找到敌人", error_msg)
            else:
                QMessageBox.critical(self, "获取失败", error_msg)
            self.status_bar.showMessage("获取PRTS数据失败")

    def _on_prts_thread_finished(self, thread: "PrtsFetchThread") -> None:
        """线程结束后释放引用，避免悬挂 QThread 对象。"""
        thread.deleteLater()
        if self.prts_fetch_thread is thread:
            self.prts_fetch_thread = None
    
    
    def closeEvent(self, event):
        """窗口关闭事件 - 优雅清理资源"""
        try:
            with error_handler("清理资源", silent=True):
                self._render.cleanup()

                pt = self.prts_fetch_thread
                if pt is not None and pt.isRunning():
                    pt.requestInterruption()
                    if not pt.wait(3000):
                        logger.warning("PRTS拉取线程未能在预期时间内停止")
                        pt.terminate()
                        pt.wait(1000)

                if hasattr(self, "_debouncer"):
                    self._debouncer.cleanup()

                from core.optimization import get_resource_manager
                get_resource_manager().clear_caches()
        except Exception:
            pass

        event.accept()