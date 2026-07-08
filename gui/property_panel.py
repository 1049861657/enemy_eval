"""
属性编辑面板 - 敌人属性的交互式编辑界面 (重构版)
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from .card_model import CardModel
from .panels import (BasicInfoPanel, CombatStatsPanel, ResistancePanel, 
                     SkillEditorPanel, RatingPanel)
from .styles import TAB_WIDGET_STYLE
from .constants import PROPERTY_PANEL_WIDTH, PROPERTY_PANEL_MIN_HEIGHT




class PropertyPanel(QWidget):
    """属性编辑面板 - 重构版，使用模块化子面板"""
    
    def __init__(self, card_model: CardModel, parent=None):
        super().__init__(parent)
        self.card_model = card_model
        
        self.setFixedWidth(PROPERTY_PANEL_WIDTH)
        self.setMinimumHeight(PROPERTY_PANEL_MIN_HEIGHT)
        
        self._create_ui()
        self._connect_signals()
        self._refresh_from_model()
    
    def _create_ui(self):
        """创建用户界面"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(TAB_WIDGET_STYLE)
        layout.addWidget(self.tab_widget)
        
        # 创建各个子面板
        self.basic_panel = BasicInfoPanel(self.card_model)
        self.combat_panel = CombatStatsPanel(self.card_model)
        self.resistance_panel = ResistancePanel(self.card_model)
        self.skills_panel = SkillEditorPanel(self.card_model)
        self.rating_panel = RatingPanel(self.card_model)
        
        # 添加到标签页
        self.tab_widget.addTab(self.basic_panel, "基础信息")
        self.tab_widget.addTab(self.combat_panel, "战斗属性")
        self.tab_widget.addTab(self.resistance_panel, "异常抗性")
        self.tab_widget.addTab(self.skills_panel, "技能天赋")
        self.tab_widget.addTab(self.rating_panel, "评价")
    
    
    
    
    
    
    def _connect_signals(self):
        """连接子面板信号与槽"""
        self._connect_model_signals()
        if getattr(self, '_signals_connected', False):
            return
        # 基础信息面板
        self.basic_panel.propertyChanged.connect(self._update_property)
        
        # 战斗属性面板
        self.combat_panel.propertyChanged.connect(self._update_property)
        
        # 异常抗性面板
        self.resistance_panel.resistanceChanged.connect(self._update_resistance)
        
        # 技能面板
        self.skills_panel.skillChanged.connect(self._on_skill_changed)
        self.skills_panel.skillsUpdated.connect(self._update_skills)
        self.skills_panel.talentsChanged.connect(lambda text: self._update_property('talents_abilities', text))
        
        # 评价面板
        self.rating_panel.ratingChanged.connect(self._update_property)
        self.rating_panel.descriptionChanged.connect(lambda text: self._update_property('brief_description', text))
        self.rating_panel.commentChanged.connect(lambda text: self._update_property('brief_comment', text))
        
        # 处理攻击方式变化的特殊逻辑
        self.basic_panel.propertyChanged.connect(self._handle_attack_type_change)
        self._signals_connected = True

    def _connect_model_signals(self):
        """连接 card_model 自身的信号；随 set_card_model 每次换绑新模型实例，不受 _signals_connected 幂等守卫影响。"""
        self.card_model.validationFailed.connect(self._on_validation_failed)

    def _on_validation_failed(self, property_name: str, error_message: str):
        """属性校验失败：模型已拒绝该次更新，UI 仍显示用户刚输入的新值——刷新为模型当前真实值以消除不一致。"""
        self._refresh_from_model()

    def _update_property(self, property_name: str, value):
        """更新属性"""
        self.card_model.update_property(property_name, value)
    
    def _update_resistance(self, resistance_name: str, value: float):
        """更新异常抗性"""
        self.card_model.update_abnormal_resistance(resistance_name, value)
    
    def _handle_attack_type_change(self, property_name: str, value):
        """处理攻击方式变化"""
        if property_name == 'attack_type':
            # 通知战斗面板更新攻击范围控制
            # 近战和不攻击类型都不能设置攻击范围
            self.combat_panel.set_attack_range_enabled(value not in ["近战", "不攻击"])
    def _on_skill_changed(self, skill_index: int, skill_data: dict):
        """技能变化处理"""
        self.card_model.update_skill(skill_index, skill_data)
    
    def _update_skills(self, skills_data: list):
        """更新技能列表"""
        self.card_model.update_property('skills', skills_data)
    def _refresh_from_model(self):
        """从模型刷新UI数据"""
        # 刷新各个子面板
        self.basic_panel.refresh_from_model()
        self.combat_panel.refresh_from_model()
        self.resistance_panel.refresh_from_model()
        self.skills_panel.refresh_from_model()
        self.rating_panel.refresh_from_model()
    def set_card_model(self, card_model: CardModel):
        """设置新的数据模型"""
        self.card_model = card_model
        
        # 更新各个子面板的数据模型
        self.basic_panel.set_card_model(card_model)
        self.combat_panel.set_card_model(card_model)
        self.resistance_panel.set_card_model(card_model)
        self.skills_panel.set_card_model(card_model)
        self.rating_panel.set_card_model(card_model)
        
        self._connect_signals()
        self._refresh_from_model()
    
    def refresh_from_model(self):
        """外部调用刷新接口"""
        self._refresh_from_model()