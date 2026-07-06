"""
战斗属性面板 - 处理敌人的战斗相关数值编辑
"""

from typing import Optional
from PySide6.QtWidgets import (QWidget, QFormLayout, QSpinBox, QDoubleSpinBox, QScrollArea)
from PySide6.QtCore import Signal

from ..card_model import CardModel
from ..styles import SPINBOX_NO_BUTTONS_STYLE


class CombatStatsPanel(QWidget):
    """战斗属性编辑面板"""
    
    propertyChanged = Signal(str, object)  # 属性变化信号
    
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
        layout = QFormLayout(scroll_widget)
        
        # 生命相关
        self.max_hp_spin = QSpinBox()
        self.max_hp_spin.setRange(1, 999999)
        self.max_hp_spin.setValue(1000)
        self.max_hp_spin.setStyleSheet(SPINBOX_NO_BUTTONS_STYLE)
        layout.addRow("最大生命值:", self.max_hp_spin)
        
        self.hp_recovery_spin = QDoubleSpinBox()
        self.hp_recovery_spin.setRange(0, 10000)
        self.hp_recovery_spin.setDecimals(1)
        self.hp_recovery_spin.setStyleSheet(SPINBOX_NO_BUTTONS_STYLE)
        layout.addRow("生命自回速度:", self.hp_recovery_spin)
        
        # 攻击相关
        self.attack_spin = QSpinBox()
        self.attack_spin.setRange(0, 999999)
        self.attack_spin.setValue(100)
        self.attack_spin.setStyleSheet(SPINBOX_NO_BUTTONS_STYLE)
        layout.addRow("攻击力:", self.attack_spin)
        
        self.attack_interval_spin = QDoubleSpinBox()
        self.attack_interval_spin.setRange(0.1, 10.0)
        self.attack_interval_spin.setDecimals(1)
        self.attack_interval_spin.setValue(2.0)
        self.attack_interval_spin.setStyleSheet(SPINBOX_NO_BUTTONS_STYLE)
        layout.addRow("攻击间隔:", self.attack_interval_spin)
        
        self.attack_range_spin = QDoubleSpinBox()
        self.attack_range_spin.setRange(0.0, 10.0)
        self.attack_range_spin.setDecimals(1)
        self.attack_range_spin.setValue(1.0)
        self.attack_range_spin.setStyleSheet(SPINBOX_NO_BUTTONS_STYLE)
        layout.addRow("攻击范围半径:", self.attack_range_spin)
        
        # 防御相关
        self.defense_spin = QSpinBox()
        self.defense_spin.setRange(0, 999999)
        self.defense_spin.setValue(50)
        self.defense_spin.setStyleSheet(SPINBOX_NO_BUTTONS_STYLE)
        layout.addRow("防御力:", self.defense_spin)
        
        self.magic_resistance_spin = QSpinBox()
        self.magic_resistance_spin.setRange(0, 100)
        self.magic_resistance_spin.setValue(10)
        self.magic_resistance_spin.setStyleSheet(SPINBOX_NO_BUTTONS_STYLE)
        layout.addRow("法术抗性:", self.magic_resistance_spin)
        
        self.damage_resistance_spin = QSpinBox()
        self.damage_resistance_spin.setRange(0, 100)
        self.damage_resistance_spin.setStyleSheet(SPINBOX_NO_BUTTONS_STYLE)
        layout.addRow("损伤抗性:", self.damage_resistance_spin)
        
        self.element_resistance_spin = QSpinBox()
        self.element_resistance_spin.setRange(0, 100)
        self.element_resistance_spin.setStyleSheet(SPINBOX_NO_BUTTONS_STYLE)
        layout.addRow("元素抗性:", self.element_resistance_spin)
        
        # 移动相关
        self.move_speed_spin = QDoubleSpinBox()
        self.move_speed_spin.setRange(0.1, 5.0)
        self.move_speed_spin.setDecimals(2)
        self.move_speed_spin.setValue(1.0)
        self.move_speed_spin.setStyleSheet(SPINBOX_NO_BUTTONS_STYLE)
        layout.addRow("移动速度:", self.move_speed_spin)
        
        self.weight_spin = QSpinBox()
        self.weight_spin.setRange(0, 10)
        self.weight_spin.setValue(1)
        layout.addRow("重量等级:", self.weight_spin)
        
        # 其他
        self.taunt_spin = QSpinBox()
        self.taunt_spin.setRange(0, 10)
        layout.addRow("基础嘲讽等级:", self.taunt_spin)
        
        self.target_value_spin = QSpinBox()
        self.target_value_spin.setRange(0, 50)
        self.target_value_spin.setValue(1)
        layout.addRow("目标价值:", self.target_value_spin)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        # 主布局
        main_layout = QFormLayout(self)
        main_layout.addWidget(scroll_area)
    
    def _connect_signals(self):
        """连接信号与槽"""
        if not self.card_model or getattr(self, '_signals_connected', False):
            return

        self.max_hp_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('max_hp', self.max_hp_spin.value()))
        self.hp_recovery_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('hp_recovery_speed', self.hp_recovery_spin.value()))
        self.attack_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('attack', self.attack_spin.value()))
        self.attack_interval_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('attack_interval', self.attack_interval_spin.value()))
        self.attack_range_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('attack_range_radius', self.attack_range_spin.value()))
        self.defense_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('defense', self.defense_spin.value()))
        self.magic_resistance_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('magic_resistance', self.magic_resistance_spin.value()))
        self.damage_resistance_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('damage_resistance', self.damage_resistance_spin.value()))
        self.element_resistance_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('element_resistance', self.element_resistance_spin.value()))
        self.move_speed_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('move_speed', self.move_speed_spin.value()))
        self.weight_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('weight_level', self.weight_spin.value()))
        self.taunt_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('base_taunt_level', self.taunt_spin.value()))
        self.target_value_spin.valueChanged.connect(
            lambda: self.propertyChanged.emit('target_value', self.target_value_spin.value()))
        self._signals_connected = True
    
    def set_attack_range_enabled(self, enabled: bool):
        """设置攻击范围是否可编辑"""
        self.attack_range_spin.setEnabled(enabled)
        if not enabled:
            self.attack_range_spin.setValue(0.0)
        elif self.attack_range_spin.value() == 0.0:
            self.attack_range_spin.setValue(1.0)
    
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
        spins = (
            self.max_hp_spin, self.hp_recovery_spin, self.attack_spin,
            self.attack_interval_spin, self.attack_range_spin, self.defense_spin,
            self.magic_resistance_spin, self.damage_resistance_spin,
            self.element_resistance_spin, self.move_speed_spin,
            self.weight_spin, self.taunt_spin, self.target_value_spin,
        )
        for spin in spins:
            spin.blockSignals(True)
        try:
            self.max_hp_spin.setValue(data.max_hp)
            self.hp_recovery_spin.setValue(data.hp_recovery_speed)
            self.attack_spin.setValue(data.attack)
            self.attack_interval_spin.setValue(data.attack_interval)
            self.attack_range_spin.setValue(data.attack_range_radius)

            # 应用攻击方式的控制逻辑
            if data.attack_type in ["近战", "不攻击"]:
                self.attack_range_spin.setEnabled(False)
            else:
                self.attack_range_spin.setEnabled(True)

            self.defense_spin.setValue(data.defense)
            self.magic_resistance_spin.setValue(data.magic_resistance)
            self.damage_resistance_spin.setValue(data.damage_resistance)
            self.element_resistance_spin.setValue(data.element_resistance)
            self.move_speed_spin.setValue(data.move_speed)
            self.weight_spin.setValue(data.weight_level)
            self.taunt_spin.setValue(data.base_taunt_level)
            self.target_value_spin.setValue(data.target_value)
        finally:
            for spin in spins:
                spin.blockSignals(False)
    
    def refresh_from_model(self):
        """外部调用刷新接口"""
        self._refresh_from_model()