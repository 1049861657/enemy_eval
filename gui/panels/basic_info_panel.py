"""
基础信息面板 - 处理敌人的基本属性编辑
"""

from typing import Optional
from PySide6.QtWidgets import (QWidget, QFormLayout, QLineEdit, QComboBox, 
                               QHBoxLayout, QPushButton, QFileDialog, QScrollArea)
from PySide6.QtCore import Signal

from ..card_model import CardModel
from utils import FixedDebouncer


class BasicInfoPanel(QWidget):
    """基础信息编辑面板"""
    
    propertyChanged = Signal(str, object)  # 属性变化信号
    
    def __init__(self, card_model: Optional[CardModel] = None, parent=None):
        super().__init__(parent)
        self.card_model = card_model
        self._syncing_ui = False
        self._name_debouncer = FixedDebouncer(self, self._emit_name_changed, 220)
        self._avatar_debouncer = FixedDebouncer(self, self._emit_avatar_changed, 220)
        self._create_ui()
        if card_model:
            self._connect_signals()
            self._refresh_from_model()
    
    def _create_ui(self):
        """创建用户界面"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QFormLayout(scroll_widget)
        
        # 敌人名称
        self.name_edit = QLineEdit()
        layout.addRow("敌人名称:", self.name_edit)
        
        # 等级
        self.grade_combo = QComboBox()
        self.grade_combo.addItems(['S', 'A', 'B', 'C', 'D'])
        layout.addRow("等级:", self.grade_combo)
        
        # 头像选择
        avatar_layout = QHBoxLayout()
        self.avatar_edit = QLineEdit()
        self.avatar_edit.setPlaceholderText("头像文件路径")
        self.avatar_btn = QPushButton("选择头像")
        self.avatar_btn.clicked.connect(self._select_avatar)
        avatar_layout.addWidget(self.avatar_edit)
        avatar_layout.addWidget(self.avatar_btn)
        layout.addRow("头像:", avatar_layout)
        
        # 攻击方式
        self.attack_type_combo = QComboBox()
        self.attack_type_combo.addItems(['近战', '远程', '近战/远程','不攻击'])
        layout.addRow("攻击方式:", self.attack_type_combo)
        
        # 伤害类型
        self.damage_type_combo = QComboBox()
        self.damage_type_combo.addItems(['物理', '法术','治疗','无'])
        layout.addRow("伤害类型:", self.damage_type_combo)
        
        # 行动方式
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems(['地面', '飞行'])
        layout.addRow("行动方式:", self.action_type_combo)
        
        # 地位
        self.position_combo = QComboBox()
        self.position_combo.addItems(['普通', '精英', '领袖'])
        layout.addRow("地位:", self.position_combo)
        
        # 种类
        self.category_combo = QComboBox()
        self.category_combo.addItems(['感染生物', '无人机', '萨卡兹', '宿主', '海怪', 
                                      '法术造物', '源石造物', '化物', '机械', '野生动物', 
                                      '坍缩体', '其他'])
        self.category_combo.setCurrentText('其他')
        layout.addRow("种类:", self.category_combo)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        # 主布局
        main_layout = QFormLayout(self)
        main_layout.addWidget(scroll_area)

    def _schedule_name_changed(self):
        if self._syncing_ui:
            return
        self._name_debouncer.schedule()

    def _emit_name_changed(self):
        self.propertyChanged.emit("name", self.name_edit.text())

    def _schedule_avatar_changed(self):
        if self._syncing_ui:
            return
        self._avatar_debouncer.schedule()

    def _emit_avatar_changed(self):
        self.propertyChanged.emit("avatar_path", self.avatar_edit.text())

    def _connect_signals(self):
        """连接信号与槽"""
        if not self.card_model or getattr(self, '_signals_connected', False):
            return

        self.name_edit.textChanged.connect(self._schedule_name_changed)
        self.grade_combo.currentTextChanged.connect(
            lambda: self.propertyChanged.emit('grade', self.grade_combo.currentText()))
        self.avatar_edit.textChanged.connect(self._schedule_avatar_changed)
        self.attack_type_combo.currentTextChanged.connect(
            lambda: self.propertyChanged.emit('attack_type', self.attack_type_combo.currentText()))
        self.damage_type_combo.currentTextChanged.connect(
            lambda: self.propertyChanged.emit('damage_type', self.damage_type_combo.currentText()))
        self.action_type_combo.currentTextChanged.connect(
            lambda: self.propertyChanged.emit('action_type', self.action_type_combo.currentText()))
        self.position_combo.currentTextChanged.connect(
            lambda: self.propertyChanged.emit('position', self.position_combo.currentText()))
        self.category_combo.currentTextChanged.connect(
            lambda: self.propertyChanged.emit('category', self.category_combo.currentText()))
        self._signals_connected = True
    
    def _select_avatar(self):
        """选择头像文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择头像", "", "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
        )
        if file_path:
            self.avatar_edit.setText(file_path)
    
    def set_card_model(self, card_model: CardModel):
        """设置数据模型"""
        self.card_model = card_model
        self._connect_signals()
        self._refresh_from_model()
    
    def _refresh_from_model(self):
        """从模型刷新UI数据"""
        if not self.card_model:
            return

        self._name_debouncer.stop()
        self._avatar_debouncer.stop()
        self._syncing_ui = True
        try:
            data = self.card_model.enemy_data
            self.name_edit.setText(data.name)
            self.grade_combo.setCurrentText(data.grade)
            self.avatar_edit.setText(data.avatar_path or "")
            self.attack_type_combo.setCurrentText(data.attack_type)
            self.damage_type_combo.setCurrentText(data.damage_type)
            self.action_type_combo.setCurrentText(data.action_type)
            self.position_combo.setCurrentText(data.position)
            self.category_combo.setCurrentText(data.category)
        finally:
            self._syncing_ui = False
    
    def refresh_from_model(self):
        """外部调用刷新接口"""
        self._refresh_from_model()