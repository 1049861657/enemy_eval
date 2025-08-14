"""
主窗口 - 敌人评价卡片实时编辑器主界面
"""
from pathlib import Path

import skia
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QSplitter, QStatusBar, QFileDialog,
                               QMessageBox, QProgressBar)

from core import EnemyCardGenerator
from .card_model import CardModel
from .preview_widget import PreviewWidget
from .property_panel import PropertyPanel


class CardGeneratorThread(QThread):
    """卡片生成线程，避免UI阻塞"""
    
    cardGenerated = Signal(object)  # 生成完成信号，传递QPixmap对象
    errorOccurred = Signal(str)  # 错误信号
    
    def __init__(self, enemy_data, save_to_file=False, output_path=None):
        super().__init__()
        self.enemy_data = enemy_data
        self.save_to_file = save_to_file
        self.output_path = output_path
        
    def run(self):
        """在后台线程中生成卡片"""
        try:
            generator = EnemyCardGenerator()
            
            if self.save_to_file:
                # 保存到文件模式
                output_path = generator.generate_card(self.enemy_data, self.output_path)
                self.cardGenerated.emit(output_path)
            else:
                # 内存预览模式
                skia_image = generator.generate_card_image(self.enemy_data)
                
                # 转换为QPixmap
                width = skia_image.width()
                height = skia_image.height()
                
                # 获取图像数据
                image_info = skia.ImageInfo.MakeN32Premul(width, height)
                row_bytes = width * 4
                
                # 创建缓冲区
                import array
                pixel_buffer = array.array('B', [0] * (width * height * 4))
                
                # 读取像素数据
                success = skia_image.readPixels(image_info, pixel_buffer, row_bytes, 0, 0)
                if not success:
                    raise Exception("无法读取图像像素数据")
                
                pixels = bytes(pixel_buffer)
                
                # 创建QImage - 修复颜色问题
                from PySide6.QtGui import QImage, QPixmap
                qimage = QImage(pixels, width, height, QImage.Format.Format_RGBA8888_Premultiplied)
                # 转换颜色通道顺序 BGRA -> RGBA
                qimage = qimage.rgbSwapped()
                qpixmap = QPixmap.fromImage(qimage)
                
                self.cardGenerated.emit(qpixmap)
                
        except Exception as e:
            self.errorOccurred.emit(str(e))


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.card_model = CardModel(self)
        self.generator_thread = None
        self.last_generated_path = ""
        self.last_generated_pixmap = None
        
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
        style_path = Path(__file__).parent / "styles.qss"
        if style_path.exists():
            with open(style_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
    
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
        """数据变化时的处理"""
        # 使用防抖动：延迟500毫秒后生成，避免频繁更新
        if hasattr(self, '_update_timer'):
            self._update_timer.stop()
        
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._generate_card)
        self._update_timer.start(500)  # 500毫秒延迟
    
    def _generate_card(self):
        """生成卡片"""
        if self.generator_thread and self.generator_thread.isRunning():
            return  # 避免重复生成
        
        self.status_bar.showMessage("正在生成卡片...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        
        # 启动生成线程（内存预览模式）
        self.generator_thread = CardGeneratorThread(self.card_model.enemy_data, save_to_file=False)
        self.generator_thread.cardGenerated.connect(self._on_card_generated)
        self.generator_thread.errorOccurred.connect(self._on_generation_error)
        self.generator_thread.start()
    
    def _on_card_generated(self, result):
        """卡片生成完成"""
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
    
    def _on_generation_error(self, error_message: str):
        """生成错误处理"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("生成失败")
        
        QMessageBox.critical(self, "生成错误", f"卡片生成失败:\n{error_message}")
    
    def _new_card(self):
        """新建卡片"""
        reply = QMessageBox.question(self, "新建卡片", "是否要丢弃当前数据并创建新卡片？")
        if reply == QMessageBox.StandardButton.Yes:
            self.card_model = CardModel(self)
            self.property_panel.set_card_model(self.card_model)
            self._connect_signals()
            self._generate_card()
    
    def _open_file(self):
        """打开配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开配置文件", "", "JSON文件 (*.json);;所有文件 (*)"
        )
        
        if file_path:
            if self.card_model.load_from_file(file_path):
                self.property_panel.refresh_from_model()
                self.status_bar.showMessage(f"已加载: {Path(file_path).name}")
            else:
                QMessageBox.warning(self, "加载失败", "无法加载配置文件，请检查文件格式。")
    
    def _save_config(self):
        """保存配置文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存配置文件", f"{self.card_model.enemy_data.name}_config.json", 
            "JSON文件 (*.json);;所有文件 (*)"
        )
        
        if file_path:
            if self.card_model.save_to_file(file_path):
                self.status_bar.showMessage(f"已保存: {Path(file_path).name}")
            else:
                QMessageBox.warning(self, "保存失败", "无法保存配置文件。")
    
    def _export_image(self):
        """导出图片"""
        if not hasattr(self, 'last_generated_pixmap') or self.last_generated_pixmap is None:
            QMessageBox.information(self, "提示", "请先生成卡片。")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出图片", f"{self.card_model.enemy_data.name}_{self.card_model.enemy_data.grade}.png",
            "PNG图片 (*.png);;JPG图片 (*.jpg);;所有文件 (*)"
        )
        
        if file_path:
            try:
                # 直接从内存中的QPixmap保存
                self.last_generated_pixmap.save(file_path)
                self.status_bar.showMessage(f"已导出: {Path(file_path).name}")
                QMessageBox.information(self, "导出成功", f"图片已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"无法导出图片:\n{str(e)}")
    
    def _reset_data(self):
        """重置数据"""
        reply = QMessageBox.question(self, "重置数据", "是否要重置所有数据到默认值？")
        if reply == QMessageBox.StandardButton.Yes:
            self._new_card()
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
            "敌人评价卡片实时编辑器 v1.0\\n\\n"
            "一个现代化的敌人评价卡片生成工具\\n"
            "支持实时预览和属性编辑\\n\\n"
            "技术栈: Python 3.12 + PySide6 + Skia-Python"
        )
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.generator_thread and self.generator_thread.isRunning():
            self.generator_thread.quit()
            self.generator_thread.wait()
        
        event.accept()