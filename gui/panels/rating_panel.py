"""
评价面板 - 处理敌人的评级和简评编辑
"""

import math
from typing import Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTextEdit, QFrame, QScrollArea, QMenu)
from PySide6.QtCore import Signal, Qt, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QPolygon

from ..card_model import CardModel
from ..detailed_editor_dialog import DetailedEditorDialog
from ..styles import (STAR_RATING_STYLE, RATING_GROUP_STYLE, DESCRIPTION_GROUP_STYLE,
                     COMMENT_GROUP_STYLE, RATING_TITLE_STYLE, DESCRIPTION_TITLE_STYLE,
                     COMMENT_TITLE_STYLE, CONTENT_AREA_STYLE, RATING_LABEL_STYLE,
                     DETAILED_TEXT_EDIT_STYLE)


class StarRatingWidget(QWidget):
    """星级评价组件"""
    
    valueChanged = Signal(int)  # 评级值变化信号
    
    def __init__(self, max_stars=5, current_value=3):
        super().__init__()
        self.max_stars = max_stars
        self.current_value = current_value
        self.hover_value = 0
        
        self.setFixedSize(140, 30)
        self.setMouseTracking(True)
        self.setStyleSheet(STAR_RATING_STYLE)
    
    def setValue(self, value):
        """设置评级值"""
        if 1 <= value <= self.max_stars:
            self.current_value = value
            self.update()
            self.valueChanged.emit(value)
    
    def getValue(self):
        """获取当前评级值"""
        return self.current_value
    
    def paintEvent(self, event):
        """绘制星星"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        star_size = 20
        spacing = 4
        start_x = (self.width() - (self.max_stars * star_size + (self.max_stars - 1) * spacing)) // 2
        start_y = (self.height() - star_size) // 2
        
        for i in range(self.max_stars):
            x = start_x + i * (star_size + spacing)
            y = start_y
            
            # 确定星星状态
            display_value = self.hover_value if self.hover_value > 0 else self.current_value
            
            if i < display_value:
                # 已选中的星星 - 金色
                painter.setBrush(QColor(255, 215, 0))  # 金色
                painter.setPen(QPen(QColor(255, 193, 7), 1))
            else:
                # 未选中的星星 - 灰色
                painter.setBrush(QColor(220, 220, 220))
                painter.setPen(QPen(QColor(180, 180, 180), 1))
            
            # 绘制星星路径 (简化的五角星)
            self._draw_star(painter, x + star_size // 2, y + star_size // 2, star_size // 3)
    
    def _draw_star(self, painter, center_x, center_y, radius):
        """绘制五角星"""
        points = []
        for i in range(10):
            angle = i * math.pi / 5
            if i % 2 == 0:
                r = radius
            else:
                r = radius * 0.4
            x = center_x + r * math.cos(angle - math.pi / 2)
            y = center_y + r * math.sin(angle - math.pi / 2)
            points.append((int(x), int(y)))
        
        polygon = QPolygon([QPoint(x, y) for x, y in points])
        painter.drawPolygon(polygon)
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            star_width = self.width() / self.max_stars
            clicked_star = int(event.position().x() / star_width) + 1
            clicked_star = max(1, min(clicked_star, self.max_stars))
            self.setValue(clicked_star)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        star_width = self.width() / self.max_stars
        hover_star = int(event.position().x() / star_width) + 1
        hover_star = max(0, min(hover_star, self.max_stars))
        
        if hover_star != self.hover_value:
            self.hover_value = hover_star
            self.update()
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.hover_value = 0
        self.update()


class RatingPanel(QWidget):
    """评价编辑面板"""
    
    ratingChanged = Signal(str, int)   # 评级变化信号
    descriptionChanged = Signal(str)   # 描述变化信号
    commentChanged = Signal(str)       # 评价变化信号
    
    def __init__(self, card_model: Optional[CardModel] = None, parent=None):
        super().__init__(parent)
        self.card_model = card_model
        self._create_ui()
        if card_model:
            self._connect_signals()
            self._refresh_from_model()
    
    def _create_ui(self):
        """创建用户界面"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(8)
        
        # === 评级部分 ===
        rating_group = QFrame()
        rating_group.setFrameStyle(QFrame.Shape.Box)
        rating_group.setStyleSheet(RATING_GROUP_STYLE)
        rating_main_layout = QVBoxLayout(rating_group)
        rating_main_layout.setSpacing(0)
        rating_main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 评级标题栏
        rating_title_label = QLabel("📊 评级 (各项评级范围: 1-5星)")
        rating_title_label.setStyleSheet(RATING_TITLE_STYLE)
        rating_main_layout.addWidget(rating_title_label)
        
        # 评级内容区域
        rating_content_widget = QWidget()
        rating_content_widget.setStyleSheet(CONTENT_AREA_STYLE)
        rating_content_layout = QVBoxLayout(rating_content_widget)
        rating_content_layout.setContentsMargins(15, 15, 15, 15)
        
        # 评级项目 - 简洁的星级评价布局
        rating_items_layout = QVBoxLayout()
        rating_items_layout.setSpacing(16)
        
        # 对策度评级
        hostility_layout = QHBoxLayout()
        hostility_layout.setSpacing(8)
        
        hostility_label = QLabel("🎯 对策度")
        hostility_label.setStyleSheet(RATING_LABEL_STYLE)
        hostility_label.setFixedWidth(110)
        self.hostility_rating = StarRatingWidget(5, 3)
        
        hostility_layout.addWidget(hostility_label)
        hostility_layout.addWidget(self.hostility_rating)
        hostility_layout.addStretch()
        
        # 创新度评级
        innovation_layout = QHBoxLayout()
        innovation_layout.setSpacing(8)
        
        innovation_label = QLabel("💡 创新度")
        innovation_label.setStyleSheet(RATING_LABEL_STYLE)
        innovation_label.setFixedWidth(110)
        self.innovation_rating = StarRatingWidget(5, 3)
        
        innovation_layout.addWidget(innovation_label)
        innovation_layout.addWidget(self.innovation_rating)
        innovation_layout.addStretch()
        
        # 威胁度评级
        threat_layout = QHBoxLayout()
        threat_layout.setSpacing(8)
        
        threat_label = QLabel("⚡ 威胁度")
        threat_label.setStyleSheet(RATING_LABEL_STYLE)
        threat_label.setFixedWidth(110)
        self.threat_rating = StarRatingWidget(5, 3)
        
        threat_layout.addWidget(threat_label)
        threat_layout.addWidget(self.threat_rating)
        threat_layout.addStretch()
        
        # 添加到布局
        rating_items_layout.addLayout(hostility_layout)
        rating_items_layout.addLayout(innovation_layout)
        rating_items_layout.addLayout(threat_layout)
        
        rating_content_layout.addLayout(rating_items_layout)
        rating_main_layout.addWidget(rating_content_widget)
        layout.addWidget(rating_group)
        
        # === 敌人描述部分 ===  
        description_group = QFrame()
        description_group.setFrameStyle(QFrame.Shape.Box)
        description_group.setStyleSheet(DESCRIPTION_GROUP_STYLE)
        description_main_layout = QVBoxLayout(description_group)
        description_main_layout.setSpacing(0)
        description_main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 敌人描述标题栏
        description_title_label = QLabel("📋 敌人描述")
        description_title_label.setStyleSheet(DESCRIPTION_TITLE_STYLE)
        description_main_layout.addWidget(description_title_label)
        
        # 敌人描述内容区域
        description_content_widget = QWidget()
        description_content_widget.setStyleSheet(CONTENT_AREA_STYLE)
        description_content_layout = QVBoxLayout(description_content_widget)
        description_content_layout.setContentsMargins(15, 15, 15, 15)
        
        # 简要描述
        self.brief_description_edit = QTextEdit()
        self.brief_description_edit.setMinimumHeight(120)
        self.brief_description_edit.setMaximumHeight(160)
        self.brief_description_edit.setPlaceholderText("敌人的基本特点和能力描述...")
        self.brief_description_edit.setStyleSheet(DETAILED_TEXT_EDIT_STYLE)
        self._setup_text_edit_events(self.brief_description_edit, "敌人描述详细编辑")
        description_content_layout.addWidget(self.brief_description_edit)
        description_main_layout.addWidget(description_content_widget)
        
        layout.addWidget(description_group)
        
        # === 简要评价部分 ===
        comment_group = QFrame()
        comment_group.setFrameStyle(QFrame.Shape.Box)
        comment_group.setStyleSheet(COMMENT_GROUP_STYLE)
        comment_main_layout = QVBoxLayout(comment_group)
        comment_main_layout.setSpacing(0)
        comment_main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 简评标题栏
        comment_title_label = QLabel("💬 简要评价")
        comment_title_label.setStyleSheet(COMMENT_TITLE_STYLE)
        comment_main_layout.addWidget(comment_title_label)
        
        # 简评内容区域
        comment_content_widget = QWidget()
        comment_content_widget.setStyleSheet(CONTENT_AREA_STYLE)
        comment_content_layout = QVBoxLayout(comment_content_widget)
        comment_content_layout.setContentsMargins(15, 15, 15, 15)
        
        # 简评内容
        self.brief_comment_edit = QTextEdit()
        self.brief_comment_edit.setMinimumHeight(120)
        self.brief_comment_edit.setMaximumHeight(160)
        self.brief_comment_edit.setPlaceholderText("对敌人的整体评价...")
        self.brief_comment_edit.setStyleSheet(DETAILED_TEXT_EDIT_STYLE)
        self._setup_text_edit_events(self.brief_comment_edit, "简要评价详细编辑")
        comment_content_layout.addWidget(self.brief_comment_edit)
        comment_main_layout.addWidget(comment_content_widget)
        
        layout.addWidget(comment_group)
        layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)
    
    def _connect_signals(self):
        """连接信号与槽"""
        if not self.card_model:
            return
            
        # 评级
        self.hostility_rating.valueChanged.connect(
            lambda value: self.ratingChanged.emit('hostility_rating', value))
        self.innovation_rating.valueChanged.connect(
            lambda value: self.ratingChanged.emit('innovation_rating', value))
        self.threat_rating.valueChanged.connect(
            lambda value: self.ratingChanged.emit('threat_rating', value))
        
        # 描述和评价
        self.brief_description_edit.textChanged.connect(
            lambda: self.descriptionChanged.emit(self.brief_description_edit.toPlainText()))
        self.brief_comment_edit.textChanged.connect(
            lambda: self.commentChanged.emit(self.brief_comment_edit.toPlainText()))
    
    def set_card_model(self, card_model: CardModel):
        """设置数据模型"""
        self.card_model = card_model
        self._connect_signals()
        self._refresh_from_model()
    
    def _refresh_from_model(self):
        """从模型刷新UI数据"""
        if not self.card_model:
            return
            
        data = self.card_model.enemy_data
        
        # 评级
        self.hostility_rating.setValue(data.hostility_rating)
        self.innovation_rating.setValue(data.innovation_rating)
        self.threat_rating.setValue(data.threat_rating)
        
        # 描述和评价
        self.brief_description_edit.setPlainText(data.brief_description)
        self.brief_comment_edit.setPlainText(data.brief_comment)
    
    def refresh_from_model(self):
        """外部调用刷新接口"""
        self._refresh_from_model()
    
    def _setup_text_edit_events(self, text_edit: QTextEdit, dialog_title: str):
        """为文本编辑器设置详细编辑事件"""
        # 右键菜单事件
        def contextMenuEvent(event):
            menu = text_edit.createStandardContextMenu()
            menu.addSeparator()
            
            # 详细编辑选项
            detailed_edit_action = menu.addAction("📝 详细编辑")
            detailed_edit_action.triggered.connect(
                lambda: self._open_detailed_editor(text_edit, dialog_title)
            )
            
            menu.exec_(event.globalPos())
            event.accept()
        
        # 重写事件处理
        text_edit.contextMenuEvent = contextMenuEvent
    
    def _open_detailed_editor(self, text_edit: QTextEdit, dialog_title: str):
        """打开详细编辑对话框"""
        current_text = text_edit.toPlainText()
        placeholder = text_edit.placeholderText()
        
        accepted, new_text = DetailedEditorDialog.edit_text(
            title=dialog_title,
            initial_text=current_text,
            placeholder=placeholder,
            parent=self
        )
        
        if accepted:
            text_edit.setPlainText(new_text)