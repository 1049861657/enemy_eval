"""
属性编辑面板 - 敌人属性的交互式编辑界面
"""

from typing import Dict

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
                               QComboBox, QTextEdit, QLabel, QPushButton,
                               QFileDialog, QCheckBox, QScrollArea, QFrame)

from .card_model import CardModel
from .modern_combobox import ModernComboBox, ComboBoxSize, create_combo_box


class SkillEditWidget(QFrame):
    """技能编辑组件"""
    
    skillChanged = Signal(int, dict)  # 技能变化信号
    
    def __init__(self, skill_index: int, skill_data: Dict[str, str] = None):
        super().__init__()
        self.skill_index = skill_index
        
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("QFrame { border: 1px solid #ddd; border-radius: 4px; padding: 5px; }")
        
        layout = QFormLayout(self)
        
        # 技能名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("技能名称")
        self.name_edit.textChanged.connect(self._on_skill_changed)
        layout.addRow("名称:", self.name_edit)
        
        # 冷却时间
        self.cooldown_edit = QLineEdit()
        self.cooldown_edit.setPlaceholderText("如: 2秒")
        self.cooldown_edit.textChanged.connect(self._on_skill_changed)
        layout.addRow("冷却时间:", self.cooldown_edit)
        
        # 技力消耗
        self.cost_edit = QLineEdit()
        self.cost_edit.setPlaceholderText("如: 10")
        self.cost_edit.textChanged.connect(self._on_skill_changed)
        layout.addRow("技力消耗:", self.cost_edit)
        
        # 技能效果
        self.effect_edit = QTextEdit()
        self.effect_edit.setMaximumHeight(80)
        self.effect_edit.setPlaceholderText("技能效果描述...")
        self.effect_edit.textChanged.connect(self._on_skill_changed)
        layout.addRow("效果:", self.effect_edit)
        
        # 如果有初始数据，填入
        if skill_data:
            self.name_edit.setText(skill_data.get('名称', ''))
            self.cooldown_edit.setText(skill_data.get('冷却时间', ''))
            self.cost_edit.setText(skill_data.get('技力消耗', ''))
            self.effect_edit.setPlainText(skill_data.get('效果', ''))
    
    def _on_skill_changed(self):
        """技能数据变化"""
        skill_data = {
            '名称': self.name_edit.text(),
            '冷却时间': self.cooldown_edit.text(),
            '技力消耗': self.cost_edit.text(),
            '效果': self.effect_edit.toPlainText()
        }
        self.skillChanged.emit(self.skill_index, skill_data)
    
    def get_skill_data(self) -> Dict[str, str]:
        """获取技能数据"""
        return {
            '名称': self.name_edit.text(),
            '冷却时间': self.cooldown_edit.text(),
            '技力消耗': self.cost_edit.text(),
            '效果': self.effect_edit.toPlainText()
        }


class PropertyPanel(QWidget):
    """属性编辑面板"""
    
    def __init__(self, card_model: CardModel, parent=None):
        super().__init__(parent)
        self.card_model = card_model
        self.skill_widgets = []
        
        self.setFixedWidth(400)
        self.setMinimumHeight(600)
        
        self._create_ui()
        self._connect_signals()
        self._refresh_from_model()
    
    def _create_ui(self):
        """创建用户界面"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 基础信息标签页
        self._create_basic_tab()
        
        # 战斗属性标签页
        self._create_combat_tab()
        
        # 异常抗性标签页
        self._create_resistance_tab()
        
        # 技能标签页
        self._create_skills_tab()
        
        # 评级标签页
        self._create_rating_tab()
        
        # 简评标签页
        self._create_comment_tab()
    
    def _create_basic_tab(self):
        """创建基础信息标签页"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QFormLayout(scroll_widget)
        
        # 敌人名称
        self.name_edit = QLineEdit()
        layout.addRow("敌人名称:", self.name_edit)
        
        # 等级
        self.grade_combo = create_combo_box(
            items=['S', 'A', 'B', 'C', 'D'],
            size=ComboBoxSize.MEDIUM
        )
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
        self.attack_type_combo = create_combo_box(
            items=['近战', '远程', '近战/远程']
        )
        layout.addRow("攻击方式:", self.attack_type_combo)
        
        # 伤害类型
        self.damage_type_combo = create_combo_box(
            items=['物理', '法术']
        )
        layout.addRow("伤害类型:", self.damage_type_combo)
        
        # 行动方式
        self.action_type_combo = create_combo_box(
            items=['地面', '飞行']
        )
        layout.addRow("行动方式:", self.action_type_combo)
        
        # 地位
        self.position_combo = create_combo_box(
            items=['普通', '精英', '领袖']
        )
        layout.addRow("地位:", self.position_combo)
        
        # 种类
        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("如: 感染生物")
        layout.addRow("种类:", self.category_edit)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.tab_widget.addTab(scroll_area, "基础信息")
    
    def _create_combat_tab(self):
        """创建战斗属性标签页"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QFormLayout(scroll_widget)
        
        # 生命相关
        self.max_hp_spin = QSpinBox()
        self.max_hp_spin.setRange(1, 999999)
        self.max_hp_spin.setValue(1000)
        layout.addRow("最大生命值:", self.max_hp_spin)
        
        self.hp_recovery_spin = QDoubleSpinBox()
        self.hp_recovery_spin.setRange(0, 1000)
        self.hp_recovery_spin.setDecimals(1)
        layout.addRow("生命恢复速度:", self.hp_recovery_spin)
        
        # 攻击相关
        self.attack_spin = QSpinBox()
        self.attack_spin.setRange(0, 999999)
        self.attack_spin.setValue(100)
        layout.addRow("攻击力:", self.attack_spin)
        
        self.attack_interval_spin = QDoubleSpinBox()
        self.attack_interval_spin.setRange(0.1, 10.0)
        self.attack_interval_spin.setDecimals(1)
        self.attack_interval_spin.setValue(2.0)
        layout.addRow("攻击间隔:", self.attack_interval_spin)
        
        self.attack_range_spin = QDoubleSpinBox()
        self.attack_range_spin.setRange(0.1, 10.0)
        self.attack_range_spin.setDecimals(1)
        self.attack_range_spin.setValue(1.0)
        layout.addRow("攻击范围半径:", self.attack_range_spin)
        
        # 防御相关
        self.defense_spin = QSpinBox()
        self.defense_spin.setRange(0, 999999)
        self.defense_spin.setValue(50)
        layout.addRow("防御力:", self.defense_spin)
        
        self.magic_resistance_spin = QSpinBox()
        self.magic_resistance_spin.setRange(0, 100)
        self.magic_resistance_spin.setValue(10)
        layout.addRow("法术抗性:", self.magic_resistance_spin)
        
        self.damage_resistance_spin = QSpinBox()
        self.damage_resistance_spin.setRange(0, 100)
        layout.addRow("损伤抗性:", self.damage_resistance_spin)
        
        self.element_resistance_spin = QSpinBox()
        self.element_resistance_spin.setRange(0, 100)
        layout.addRow("元素抗性:", self.element_resistance_spin)
        
        # 移动相关
        self.move_speed_spin = QDoubleSpinBox()
        self.move_speed_spin.setRange(0.1, 5.0)
        self.move_speed_spin.setDecimals(1)
        self.move_speed_spin.setValue(1.0)
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
        self.target_value_spin.setRange(0, 10)
        self.target_value_spin.setValue(1)
        layout.addRow("目标价值:", self.target_value_spin)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.tab_widget.addTab(scroll_area, "战斗属性")
    
    def _create_resistance_tab(self):
        """创建异常抗性标签页"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 异常抗性说明
        info_label = QLabel("选中表示对该异常状态有抗性 (值为1)")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)
        
        # 异常抗性复选框
        self.resistance_checkboxes = {}
        resistances = ['冰冻', '沉默', '晕眩', '沉睡', '浮空', '战栗', '恐惧', '诱导']
        
        for resistance in resistances:
            checkbox = QCheckBox(resistance)
            self.resistance_checkboxes[resistance] = checkbox
            layout.addWidget(checkbox)
        
        layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.tab_widget.addTab(scroll_area, "异常抗性")
    
    def _create_skills_tab(self):
        """创建技能标签页"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 技能说明
        info_label = QLabel("最多显示3个技能，空技能将被自动过滤")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)
        
        # 技能编辑组件
        self.skills_layout = QVBoxLayout()
        layout.addLayout(self.skills_layout)
        
        # 添加3个技能编辑组件
        for i in range(3):
            skill_widget = SkillEditWidget(i)
            skill_widget.skillChanged.connect(self._on_skill_changed)
            self.skill_widgets.append(skill_widget)
            self.skills_layout.addWidget(skill_widget)
        
        # 天赋能力
        layout.addWidget(QLabel("天赋&能力:"))
        self.talents_edit = QTextEdit()
        self.talents_edit.setMaximumHeight(100)
        self.talents_edit.setPlaceholderText("描述敌人的天赋和特殊能力...")
        layout.addWidget(self.talents_edit)
        
        layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.tab_widget.addTab(scroll_area, "技能&天赋")
    
    def _create_rating_tab(self):
        """创建评级标签页"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QFormLayout(scroll_widget)
        
        # 评级说明
        info_label = QLabel("各项评级范围: 1-5星")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addRow(info_label)
        
        # 对策度
        self.hostility_spin = QSpinBox()
        self.hostility_spin.setRange(1, 5)
        self.hostility_spin.setValue(3)
        layout.addRow("对策度:", self.hostility_spin)
        
        # 创新度
        self.innovation_spin = QSpinBox()
        self.innovation_spin.setRange(1, 5)
        self.innovation_spin.setValue(3)
        layout.addRow("创新度:", self.innovation_spin)
        
        # 威胁度
        self.threat_spin = QSpinBox()
        self.threat_spin.setRange(1, 5)
        self.threat_spin.setValue(3)
        layout.addRow("威胁度:", self.threat_spin)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.tab_widget.addTab(scroll_area, "评级")
    
    def _create_comment_tab(self):
        """创建简评标签页"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 简要描述
        layout.addWidget(QLabel("简要描述:"))
        self.brief_description_edit = QTextEdit()
        self.brief_description_edit.setMaximumHeight(100)
        self.brief_description_edit.setPlaceholderText("敌人的基本特点和能力描述...")
        layout.addWidget(self.brief_description_edit)
        
        # 简评内容
        layout.addWidget(QLabel("简评内容:"))
        self.brief_comment_edit = QTextEdit()
        self.brief_comment_edit.setMaximumHeight(100)
        self.brief_comment_edit.setPlaceholderText("对敌人的整体评价...")
        layout.addWidget(self.brief_comment_edit)
        
        layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.tab_widget.addTab(scroll_area, "简评")
    
    def _connect_signals(self):
        """连接信号与槽"""
        # 基础信息
        self.name_edit.textChanged.connect(lambda: self._update_property('name', self.name_edit.text()))
        self.grade_combo.currentTextChanged.connect(lambda: self._update_property('grade', self.grade_combo.currentText()))
        self.avatar_edit.textChanged.connect(lambda: self._update_property('avatar_path', self.avatar_edit.text()))
        self.attack_type_combo.currentTextChanged.connect(lambda: self._update_property('attack_type', self.attack_type_combo.currentText()))
        self.damage_type_combo.currentTextChanged.connect(lambda: self._update_property('damage_type', self.damage_type_combo.currentText()))
        self.action_type_combo.currentTextChanged.connect(lambda: self._update_property('action_type', self.action_type_combo.currentText()))
        self.position_combo.currentTextChanged.connect(lambda: self._update_property('position', self.position_combo.currentText()))
        self.category_edit.textChanged.connect(lambda: self._update_property('category', self.category_edit.text()))
        
        # 战斗属性
        self.max_hp_spin.valueChanged.connect(lambda: self._update_property('max_hp', self.max_hp_spin.value()))
        self.hp_recovery_spin.valueChanged.connect(lambda: self._update_property('hp_recovery_speed', self.hp_recovery_spin.value()))
        self.attack_spin.valueChanged.connect(lambda: self._update_property('attack', self.attack_spin.value()))
        self.attack_interval_spin.valueChanged.connect(lambda: self._update_property('attack_interval', self.attack_interval_spin.value()))
        self.attack_range_spin.valueChanged.connect(lambda: self._update_property('attack_range_radius', self.attack_range_spin.value()))
        self.defense_spin.valueChanged.connect(lambda: self._update_property('defense', self.defense_spin.value()))
        self.magic_resistance_spin.valueChanged.connect(lambda: self._update_property('magic_resistance', self.magic_resistance_spin.value()))
        self.damage_resistance_spin.valueChanged.connect(lambda: self._update_property('damage_resistance', self.damage_resistance_spin.value()))
        self.element_resistance_spin.valueChanged.connect(lambda: self._update_property('element_resistance', self.element_resistance_spin.value()))
        self.move_speed_spin.valueChanged.connect(lambda: self._update_property('move_speed', self.move_speed_spin.value()))
        self.weight_spin.valueChanged.connect(lambda: self._update_property('weight_level', self.weight_spin.value()))
        self.taunt_spin.valueChanged.connect(lambda: self._update_property('base_taunt_level', self.taunt_spin.value()))
        self.target_value_spin.valueChanged.connect(lambda: self._update_property('target_value', self.target_value_spin.value()))
        
        # 异常抗性
        for name, checkbox in self.resistance_checkboxes.items():
            checkbox.stateChanged.connect(lambda state, resistance=name: self._update_resistance(resistance, 1.0 if state == Qt.CheckState.Checked.value else 0.0))
        
        # 技能和天赋
        self.talents_edit.textChanged.connect(lambda: self._update_property('talents_abilities', self.talents_edit.toPlainText()))
        
        # 评级
        self.hostility_spin.valueChanged.connect(lambda: self._update_property('hostility_rating', self.hostility_spin.value()))
        self.innovation_spin.valueChanged.connect(lambda: self._update_property('innovation_rating', self.innovation_spin.value()))
        self.threat_spin.valueChanged.connect(lambda: self._update_property('threat_rating', self.threat_spin.value()))
        
        # 简评
        self.brief_description_edit.textChanged.connect(lambda: self._update_property('brief_description', self.brief_description_edit.toPlainText()))
        self.brief_comment_edit.textChanged.connect(lambda: self._update_property('brief_comment', self.brief_comment_edit.toPlainText()))
    
    def _select_avatar(self):
        """选择头像文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择头像", "", "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
        )
        if file_path:
            self.avatar_edit.setText(file_path)
    
    def _update_property(self, property_name: str, value):
        """更新属性"""
        self.card_model.update_property(property_name, value)
    
    def _update_resistance(self, resistance_name: str, value: float):
        """更新异常抗性"""
        self.card_model.update_abnormal_resistance(resistance_name, value)
    
    def _on_skill_changed(self, skill_index: int, skill_data: Dict[str, str]):
        """技能变化处理"""
        self.card_model.update_skill(skill_index, skill_data)
    
    def _refresh_from_model(self):
        """从模型刷新UI数据"""
        data = self.card_model.enemy_data
        
        # 基础信息
        self.name_edit.setText(data.name)
        self.grade_combo.setCurrentText(data.grade)
        self.avatar_edit.setText(data.avatar_path or "")
        self.attack_type_combo.setCurrentText(data.attack_type)
        self.damage_type_combo.setCurrentText(data.damage_type)
        self.action_type_combo.setCurrentText(data.action_type)
        self.position_combo.setCurrentText(data.position)
        self.category_edit.setText(data.category)
        
        # 战斗属性
        self.max_hp_spin.setValue(data.max_hp)
        self.hp_recovery_spin.setValue(data.hp_recovery_speed)
        self.attack_spin.setValue(data.attack)
        self.attack_interval_spin.setValue(data.attack_interval)
        self.attack_range_spin.setValue(data.attack_range_radius)
        self.defense_spin.setValue(data.defense)
        self.magic_resistance_spin.setValue(data.magic_resistance)
        self.damage_resistance_spin.setValue(data.damage_resistance)
        self.element_resistance_spin.setValue(data.element_resistance)
        self.move_speed_spin.setValue(data.move_speed)
        self.weight_spin.setValue(data.weight_level)
        self.taunt_spin.setValue(data.base_taunt_level)
        self.target_value_spin.setValue(data.target_value)
        
        # 异常抗性
        for name, checkbox in self.resistance_checkboxes.items():
            is_resistant = data.abnormal_resistances.get(name, 0.0) > 0
            checkbox.setChecked(is_resistant)
        
        # 技能
        for i, skill_widget in enumerate(self.skill_widgets):
            if i < len(data.skills):
                skill_data = data.skills[i]
                skill_widget.name_edit.setText(skill_data.get('名称', ''))
                skill_widget.cooldown_edit.setText(skill_data.get('冷却时间', ''))
                skill_widget.cost_edit.setText(skill_data.get('技力消耗', ''))
                skill_widget.effect_edit.setPlainText(skill_data.get('效果', ''))
            else:
                skill_widget.name_edit.clear()
                skill_widget.cooldown_edit.clear()
                skill_widget.cost_edit.clear()
                skill_widget.effect_edit.clear()
        
        # 天赋能力
        self.talents_edit.setPlainText(data.talents_abilities)
        
        # 评级
        self.hostility_spin.setValue(data.hostility_rating)
        self.innovation_spin.setValue(data.innovation_rating)
        self.threat_spin.setValue(data.threat_rating)
        
        # 简评
        self.brief_description_edit.setPlainText(data.brief_description)
        self.brief_comment_edit.setPlainText(data.brief_comment)
    
    def set_card_model(self, card_model: CardModel):
        """设置新的数据模型"""
        self.card_model = card_model
        self._connect_signals()
        self._refresh_from_model()
    
    def refresh_from_model(self):
        """外部调用刷新接口"""
        self._refresh_from_model()