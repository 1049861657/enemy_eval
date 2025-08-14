"""
异常抗性面板 - 处理敌人的异常状态抗性设置
"""

from typing import Optional, Dict
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QCheckBox, 
                               QLabel, QScrollArea)
from PySide6.QtCore import Signal, Qt

from ..card_model import CardModel
from ..styles import CHECKBOX_STYLE


class ResistancePanel(QWidget):
    """异常抗性编辑面板"""
    
    resistanceChanged = Signal(str, float)  # 抗性变化信号
    
    def __init__(self, card_model: Optional[CardModel] = None, parent=None):
        super().__init__(parent)
        self.card_model = card_model
        self.resistance_checkboxes: Dict[str, QCheckBox] = {}
        self._create_ui()
        if card_model:
            self._connect_signals()
            self._refresh_from_model()
    
    def _create_ui(self):
        """创建用户界面"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 异常抗性说明
        info_label = QLabel("选中表示对该异常状态有抗性")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)
        
        # 异常抗性复选框 - 使用网格布局
        resistances = ['冻结', '沉默', '晕眩', '沉睡', '浮空', '战栗', '恐惧', '麻痹', '诱导']
        
        # 创建网格布局容器
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(12)  # 设置间距
        grid_layout.setContentsMargins(20, 10, 20, 10)  # 设置边距
        
        # 按3列布局排列复选框
        for i, resistance in enumerate(resistances):
            checkbox = QCheckBox(resistance)
            checkbox.setStyleSheet(CHECKBOX_STYLE)
            self.resistance_checkboxes[resistance] = checkbox
            
            row = i // 3
            col = i % 3
            grid_layout.addWidget(checkbox, row, col)
        
        layout.addWidget(grid_widget)
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
            
        for name, checkbox in self.resistance_checkboxes.items():
            checkbox.stateChanged.connect(
                lambda state, resistance=name: self.resistanceChanged.emit(
                    resistance, 1.0 if state == Qt.CheckState.Checked.value else 0.0))
    
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
        for name, checkbox in self.resistance_checkboxes.items():
            is_resistant = data.abnormal_resistances.get(name, 0.0) > 0
            checkbox.setChecked(is_resistant)
    
    def refresh_from_model(self):
        """外部调用刷新接口"""
        self._refresh_from_model()