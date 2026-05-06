"""
预览组件 - 卡片图片的实时预览和交互
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont, QWheelEvent
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QScrollArea, QSlider, QSizePolicy, QFrame)


class ImageLabel(QLabel):
    """支持缩放的图片标签"""
    
    # 缩放变化信号
    scaleChanged = Signal(int)  # 发出缩放百分比
    
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("QLabel { border: 1px solid #ddd; background-color: white; }")
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.original_pixmap = None
        self.scale_factor = 1.0
        
        # 设置默认显示
        self.setText("卡片预览区域\\n\\n点击生成卡片开始预览")
        self.setStyleSheet(self.styleSheet() + "font-size: 16px; color: #999;")
        
        # 启用鼠标滚轮事件
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
        self.setMouseTracking(True)  # 启用鼠标跟踪
    
    def set_pixmap(self, pixmap: QPixmap):
        """设置图片"""
        self.original_pixmap = pixmap
        self.scale_factor = 1.0  # 恢复为1.0，让PreviewWidget计算合适的缩放
        self._update_display()
        
        # 清除默认文本样式并自动获得焦点
        self.setStyleSheet("QLabel { border: 1px solid #ddd; background-color: white; }")
        self.setFocus()  # 自动获得焦点以接收滚轮事件
    
    def set_scale_factor(self, factor: float):
        """设置缩放因子"""
        if self.original_pixmap:
            self.scale_factor = factor
            self._update_display()
    
    def _update_display(self):
        """更新显示"""
        if not self.original_pixmap:
            return
            
        # 计算缩放后的尺寸
        scaled_size = self.original_pixmap.size() * self.scale_factor
        scaled_pixmap = self.original_pixmap.scaled(
            scaled_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        
        self.setPixmap(scaled_pixmap)
    
    def get_current_pixmap(self) -> Optional[QPixmap]:
        """获取当前显示的图片"""
        return self.pixmap()
    
    def wheelEvent(self, event: QWheelEvent):
        """鼠标滚轮事件 - 缩放功能"""
        if not self.original_pixmap:
            return
            
        # 获取滚轮角度
        angle_delta = event.angleDelta().y()
        
        # 向上查找PreviewWidget获取当前百分比
        preview_widget = self.parent()
        while preview_widget and not hasattr(preview_widget, 'zoom_slider'):
            preview_widget = preview_widget.parent()
        
        if preview_widget:
            # 从滑块获取当前百分比
            current_percent = preview_widget.zoom_slider.value()
            scale_step = 10  # 每次滚动10%
            
            if angle_delta > 0:  # 向上滚动，放大
                new_percent = min(current_percent + scale_step, 200)  # 最大200%
            else:  # 向下滚动，缩小
                new_percent = max(current_percent - scale_step, 10)  # 最小10%
            
            # 发出缩放变化信号
            self.scaleChanged.emit(new_percent)
        
        event.accept()


class PreviewWidget(QWidget):
    """预览组件"""
    
    exportRequested = Signal()  # 导出请求信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_path = ""
        self.base_scale_factor = 1.0  # 基准缩放比例
        
        self._create_ui()
        self._connect_signals()
    
    def _create_ui(self):
        """创建用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 工具栏
        self._create_toolbar(layout)
        
        # 滚动区域包含图片显示
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 图片显示标签
        self.image_label = ImageLabel()
        scroll_area.setWidget(self.image_label)
        
        layout.addWidget(scroll_area)
        
        # 底部控制栏
        self._create_bottom_controls(layout)
    
    def _create_toolbar(self, parent_layout):
        """创建工具栏"""
        toolbar_frame = QFrame()
        toolbar_frame.setFrameStyle(QFrame.StyledPanel)
        toolbar_frame.setMaximumHeight(50)
        
        toolbar_layout = QHBoxLayout(toolbar_frame)
        
        # 标题
        title_label = QLabel("卡片预览")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        toolbar_layout.addWidget(title_label)
        
        toolbar_layout.addStretch()
        
        # 导出按钮
        self.export_btn = QPushButton("导出图片")
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #409eff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:disabled {
                background-color: #c0c4cc;
            }
        """)
        toolbar_layout.addWidget(self.export_btn)
        
        parent_layout.addWidget(toolbar_frame)
    
    def _create_bottom_controls(self, parent_layout):
        """创建底部控制栏"""
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel)
        controls_frame.setMaximumHeight(80)
        
        controls_layout = QVBoxLayout(controls_frame)
        
        # 缩放控制
        zoom_layout = QHBoxLayout()
        
        zoom_layout.addWidget(QLabel("缩放:"))
        
        # 缩放滑块
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 200)  # 10% 到 200%
        self.zoom_slider.setValue(100)  # 默认100%
        self.zoom_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.zoom_slider.setTickInterval(25)
        zoom_layout.addWidget(self.zoom_slider)
        
        # 缩放值显示
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(40)
        zoom_layout.addWidget(self.zoom_label)
        
        # 重置按钮
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self._reset_zoom)
        zoom_layout.addWidget(reset_btn)
        
        controls_layout.addLayout(zoom_layout)
        
        # 信息显示
        info_layout = QHBoxLayout()
        self.info_label = QLabel("就绪")
        self.info_label.setStyleSheet("color: #666; font-size: 12px;")
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        
        # 图片尺寸信息
        self.size_label = QLabel("")
        self.size_label.setStyleSheet("color: #666; font-size: 12px;")
        info_layout.addWidget(self.size_label)
        
        controls_layout.addLayout(info_layout)
        
        parent_layout.addWidget(controls_frame)
    
    def _connect_signals(self):
        """连接信号与槽"""
        self.export_btn.clicked.connect(self.exportRequested.emit)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        
        # 连接图片标签的缩放信号到滑块
        self.image_label.scaleChanged.connect(self._on_image_scale_changed)
    
    def _on_zoom_changed(self, value: int):
        """缩放滑块变化处理"""
        # 基于base_scale_factor计算实际缩放
        actual_scale = self.base_scale_factor * (value / 100.0)
        self.image_label.set_scale_factor(actual_scale)
        self.zoom_label.setText(f"{value}%")
    
    def _on_image_scale_changed(self, scale_percent: int):
        """图片缩放变化处理（来自鼠标滚轮）"""
        # 计算基于base_scale_factor的实际缩放
        actual_scale = self.base_scale_factor * (scale_percent / 100.0)
        self.image_label.set_scale_factor(actual_scale)
        
        # 更新滑块位置（避免递归）
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(scale_percent)
        self.zoom_slider.blockSignals(False)
        
        # 更新标签显示
        self.zoom_label.setText(f"{scale_percent}%")
    
    def _reset_zoom(self):
        """重置缩放"""
        self.zoom_slider.setValue(100)
    
    def load_image(self, image_path: str):
        """加载图片"""
        if not Path(image_path).exists():
            self._show_error_message(f"图片文件不存在: {image_path}")
            return
        
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                self._show_error_message("无法加载图片，请检查文件格式")
                return
            
            self.current_image_path = image_path
            self.image_label.set_pixmap(pixmap)
            self.export_btn.setEnabled(True)
            
            # 更新信息显示
            file_name = Path(image_path).name
            self.info_label.setText(f"已加载: {file_name}")
            self.size_label.setText(f"尺寸: {pixmap.width()} × {pixmap.height()}")
            
            # 重置缩放
            self._reset_zoom()
            
        except Exception as e:
            self._show_error_message(f"加载图片时发生错误: {str(e)}")
    
    def _show_error_message(self, message: str):
        """显示错误消息"""
        self.info_label.setText(f"错误: {message}")
        self.info_label.setStyleSheet("color: #f56c6c; font-size: 12px;")
        
        # 5秒后恢复正常样式
        from PySide6.QtCore import QTimer
        QTimer.singleShot(5000, lambda: self.info_label.setStyleSheet("color: #666; font-size: 12px;"))
    
    def clear_preview(self):
        """清空预览"""
        self.image_label.clear()
        self.image_label.setText("卡片预览区域\\n\\n点击生成卡片开始预览")
        self.image_label.setStyleSheet(
            "QLabel { border: 1px solid #ddd; background-color: white; font-size: 16px; color: #999; }"
        )
        
        self.current_image_path = ""
        self.export_btn.setEnabled(False)
        self.info_label.setText("就绪")
        self.size_label.setText("")
        self._reset_zoom()
    
    def load_pixmap(self, pixmap: QPixmap):
        """加载QPixmap图片（内存模式）"""
        if pixmap.isNull():
            self._show_error_message("无法加载图片数据")
            return
        
        available_width = 1200
        available_height = 800

        scale_x = available_width / pixmap.width()
        scale_y = available_height / pixmap.height()
        optimal_scale = min(scale_x, scale_y)
        
        # 设置调整后的图片到ImageLabel
        self.image_label.original_pixmap = pixmap
        self.image_label.scale_factor = optimal_scale
        self.image_label._update_display()
        
        self.export_btn.setEnabled(True)
        
        # 更新信息显示
        self.info_label.setText("内存预览已更新")
        self.size_label.setText(f"尺寸: {pixmap.width()} × {pixmap.height()}")
        
        # 设置滑块和标签，100%对应optimal_scale
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(100)  # 滑块100%对应optimal_scale
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText("100%")
        
        # 存储基准缩放比例
        self.base_scale_factor = optimal_scale
    
    def get_current_image_path(self) -> str:
        """获取当前图片路径"""
        return self.current_image_path
    
    def has_image(self) -> bool:
        """是否有图片"""
        return bool(self.current_image_path and Path(self.current_image_path).exists())