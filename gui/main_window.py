"""
主窗口 - 敌人评价卡片实时编辑器主界面
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QSplitter, QStatusBar, QFileDialog,
                               QMessageBox, QProgressBar, QInputDialog)

from utils import (
    AdaptiveDebouncer,
    CardGeneratorThread,
    EnemyEvalException,
    RenderError,
    ValidationError,
    categorize_error_message,
    error_handler,
    fetch_enemy_data,
)
from .card_model import CardModel
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
        self.generator_thread = None
        self._orphan_render_threads: list[CardGeneratorThread] = []
        self.last_generated_path = ""
        self.last_generated_pixmap = None
        self._preview_revision = 0
        self._debouncer = AdaptiveDebouncer(min_delay=200, max_delay=520)
        
        self.setWindowTitle("敌人评价卡片实时编辑器 v1.0")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)
        
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
        splitter.setSizes([400, 900])
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
        """连接信号与槽"""
        # 数据模型变化时重新生成卡片
        self.card_model.dataChanged.connect(self._on_data_changed)
        
        # 预览组件的导出信号
        self.preview_widget.exportRequested.connect(self._export_image)
    
    def _on_data_changed(self):
        """数据变化时的处理 - 使用自适应防抖"""
        self._debouncer.debounce(self._generate_card)
    
    def _release_finished_render_thread(self, thread: CardGeneratorThread) -> None:
        """旧渲染线程结束后释放 Python 引用；未完成时严禁让 GC 回收 QThread。"""
        try:
            self._orphan_render_threads.remove(thread)
        except ValueError:
            pass
        thread.deleteLater()

    def _generate_card(self):
        """生成卡片：不在主线程等待线程结束，避免打字时界面卡住。"""
        self._preview_revision += 1
        rev = self._preview_revision

        prev = self.generator_thread
        self.generator_thread = CardGeneratorThread(
            self.card_model.enemy_data, revision=rev, save_to_file=False
        )
        self.generator_thread.cardGenerated.connect(self._on_card_generated)
        self.generator_thread.errorOccurred.connect(self._on_generation_error)

        if prev is not None:
            prev.requestInterruption()
            if prev.isRunning():
                self._orphan_render_threads.append(prev)
                prev.finished.connect(
                    lambda thr=prev: self._release_finished_render_thread(thr)
                )
            else:
                prev.deleteLater()

        self.status_bar.showMessage("正在生成卡片...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.generator_thread.start()
    
    def _on_card_generated(self, result, revision: int):
        """卡片生成完成 - 忽略过期的后台结果"""
        if revision != self._preview_revision:
            return
        if hasattr(self, "last_generated_pixmap") and self.last_generated_pixmap:
            self.last_generated_pixmap = None

        if isinstance(result, str):
            # 文件路径模式（导出时）
            self.last_generated_path = result
            self.preview_widget.load_image(result)
            self.status_bar.showMessage(f"卡片已生成: {Path(result).name}")
        else:
            # QPixmap模式（预览时）
            self.preview_widget.load_pixmap(result)
            self.last_generated_pixmap = result
            self.status_bar.showMessage("卡片预览已更新")
        
        self.progress_bar.setVisible(False)
    
    def _on_generation_error(self, error_message: str, revision: int):
        """生成错误处理 - 忽略已过期任务的错误提示"""
        if revision != self._preview_revision:
            return
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("生成失败")
        
        # 使用工具函数分类错误消息
        title, message = categorize_error_message(error_message)
        
        logger.error(f"卡片生成失败: {error_message}")
        QMessageBox.critical(self, title, message)
    
    def _new_card(self):
        """新建卡片"""
        reply = QMessageBox.question(self, "新建卡片", "是否要丢弃当前数据并创建新卡片？")
        if reply == QMessageBox.StandardButton.Yes:
            self.card_model = CardModel(self)
            self.property_panel.set_card_model(self.card_model)
            self._connect_signals()
            self._generate_card()
    
    def _open_file(self):
        """打开配置文件 - 增强错误处理"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开配置文件", "", "JSON文件 (*.json);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with error_handler("加载配置文件"):
                    if self.card_model.load_from_file(file_path):
                        self.property_panel.refresh_from_model()
                        self.status_bar.showMessage(f"已加载: {Path(file_path).name}")
                        self._generate_card()  # 自动刷新预览
                    else:
                        raise ValidationError("无效的配置文件格式")
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
                    if self.card_model.save_to_file(file_path):
                        self.status_bar.showMessage(f"已保存: {Path(file_path).name}")
                    else:
                        raise ValidationError("保存操作失败")
            except EnemyEvalException as e:
                title, message = categorize_error_message(str(e))
                QMessageBox.warning(self, title, message)
    
    def _export_image(self):
        """导出图片 - 增强错误处理"""
        if not hasattr(self, 'last_generated_pixmap') or self.last_generated_pixmap is None:
            QMessageBox.information(self, "提示", "请先生成卡片。")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出图片", f"{self.card_model.enemy_data.name}_{self.card_model.enemy_data.grade}.png",
            "PNG图片 (*.png);;JPG图片 (*.jpg);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with error_handler("导出图片"):
                    # 直接从内存中的QPixmap保存
                    success = self.last_generated_pixmap.save(file_path)
                    if not success:
                        raise RenderError("图片保存失败")
                    
                    self.status_bar.showMessage(f"已导出: {Path(file_path).name}")
                    QMessageBox.information(self, "导出成功", f"图片已保存到:\n{file_path}")
            except EnemyEvalException as e:
                title, message = categorize_error_message(str(e))
                QMessageBox.critical(self, title, message)
    
    def _reset_data(self):
        """重置数据"""
        reply = QMessageBox.question(self, "重置数据", "是否要重置所有数据到默认值？")
        if reply == QMessageBox.StandardButton.Yes:
            self._new_card()
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
            "敌人评价卡片实时编辑器 v1.0\n\n"
            "一个现代化的敌人评价卡片生成工具\n"
            "支持实时预览和属性编辑\n\n"
            "技术栈: Python 3.12 + PySide6 + Skia-Python"
        )
    
    def _reference_prts(self):
        """参考PRTS功能 - 输入敌人名称获取数据"""
        enemy_name, ok = PrtsReferenceDialog.get_enemy_name_input(self,"PRTS参考")

        if ok and enemy_name:
            self._fetch_prts_data(enemy_name)
    
    def _fetch_prts_data(self, enemy_name: str):
        """获取PRTS数据并填充到当前模型"""
        self.status_bar.showMessage(f"正在从PRTS获取「{enemy_name}」的数据...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        try:
            # 使用集成的PRTS接口获取并转换数据
            enemy_data, error_msg = fetch_enemy_data(enemy_name)
            
            if enemy_data:
                # 更新卡片模型
                self.card_model.set_enemy_data(enemy_data)
                self.property_panel.refresh_from_model()
                self.status_bar.showMessage(f"已成功导入「{enemy_name}」的PRTS数据")
                self._generate_card()  # 刷新预览
                QMessageBox.information(self, "导入成功", f"已成功从PRTS导入「{enemy_name}」的数据。")
            else:
                # 处理错误
                if "未找到敌人" in error_msg:
                    QMessageBox.warning(self, "未找到敌人", error_msg)
                else:
                    QMessageBox.critical(self, "获取失败", error_msg)
                self.status_bar.showMessage("获取PRTS数据失败")
                
        except Exception as e:
            logger.error(f"PRTS数据获取失败: {e}")
            QMessageBox.critical(self, "获取失败", f"获取PRTS数据时发生错误：{str(e)}")
            self.status_bar.showMessage("获取PRTS数据失败")
        finally:
            self.progress_bar.setVisible(False)
    
    
    def closeEvent(self, event):
        """窗口关闭事件 - 优雅清理资源"""
        try:
            with error_handler("清理资源", silent=True):
                threads: list[CardGeneratorThread] = list(self._orphan_render_threads)
                if self.generator_thread is not None:
                    threads.append(self.generator_thread)
                for t in threads:
                    if t.isRunning():
                        t.requestInterruption()
                for t in threads:
                    if t.isRunning():
                        if not t.wait(3000):
                            logger.warning("渲染线程未能在预期时间内停止")
                            t.terminate()
                            t.wait(1000)

                if hasattr(self, "last_generated_pixmap") and self.last_generated_pixmap:
                    self.last_generated_pixmap = None

                if hasattr(self, "_debouncer"):
                    self._debouncer.cleanup()
        except Exception:
            pass

        event.accept()