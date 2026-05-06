"""
技能编辑面板 - 处理敌人的技能和天赋编辑
"""

from typing import Optional, List, Dict

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QTextEdit, QScrollArea)

from ..card_model import CardModel
from ..detailed_editor_dialog import DetailedEditorDialog
from ..styles import ADD_BUTTON_STYLE, TEXT_EDIT_STYLE, SKILL_EDIT_STYLE, REMOVE_BUTTON_STYLE


class DetailedTextEdit(QTextEdit):
    """支持详细编辑的文本框"""
    
    def __init__(self, title: str = "详细编辑", parent=None):
        super().__init__(parent)
        self.edit_title = title
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    
    def _show_context_menu(self, position):
        """显示右键菜单"""
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        
        # 添加详细编辑选项
        detail_action = QAction("📝 详细编辑", self)
        detail_action.triggered.connect(self._open_detailed_editor)
        menu.addAction(detail_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def _open_detailed_editor(self):
        """打开详细编辑器"""
        current_text = self.toPlainText()
        placeholder = self.placeholderText()
        
        confirmed, new_text = DetailedEditorDialog.edit_text(
            f"{self.edit_title} - 详细编辑",
            current_text,
            placeholder,
            self
        )
        
        if confirmed:
            self.setPlainText(new_text)


class SkillEditWidget(QWidget):
    """技能编辑组件"""
    
    skillChanged = Signal(int, dict)  # 技能变化信号
    removeRequested = Signal(int)     # 请求删除信号
    
    def __init__(self, skill_index: int, skill_data: Dict[str, str] = None):
        super().__init__()
        self.skill_index = skill_index
        self.setStyleSheet(SKILL_EDIT_STYLE)
        self._create_ui()
        
        # 如果有初始数据，填入
        if skill_data:
            self._load_skill_data(skill_data)
    
    def _create_ui(self):
        """创建UI"""
        from PySide6.QtWidgets import QFormLayout, QLineEdit

        layout = QVBoxLayout(self)
        
        # 添加标题栏（技能序号和删除按钮）
        header_layout = QHBoxLayout()
        skill_title = QLabel(f"技能 {self.skill_index + 1}")
        skill_title.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 14px;")
        
        self.remove_btn = QPushButton()
        self.remove_btn.setFixedSize(24, 24)
        
        # 设置删除图标
        from utils import resource_manager
        icon_path = resource_manager.get_icon_path("icons8-delete-96.png")
        self.remove_btn.setIcon(QIcon(icon_path))
        self.remove_btn.setIconSize(self.remove_btn.size())
        self.remove_btn.setStyleSheet(REMOVE_BUTTON_STYLE)
        self.remove_btn.clicked.connect(lambda: self.removeRequested.emit(self.skill_index))
        
        header_layout.addWidget(skill_title)
        header_layout.addStretch()
        header_layout.addWidget(self.remove_btn)
        layout.addLayout(header_layout)
        
        # 技能编辑表单
        form_layout = QFormLayout()
        
        # 技能名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("技能名称")
        self.name_edit.textChanged.connect(self._on_skill_changed)
        form_layout.addRow("名称:", self.name_edit)
        
        # 冷却时间
        self.cooldown_edit = QLineEdit()
        self.cooldown_edit.setPlaceholderText("如: 3/6 (初动/回转)")
        self.cooldown_edit.textChanged.connect(self._on_skill_changed)
        form_layout.addRow("冷却时间:", self.cooldown_edit)
        
        # 技力消耗
        self.cost_edit = QLineEdit()
        self.cost_edit.setPlaceholderText("可选，如: 10")
        self.cost_edit.textChanged.connect(self._on_skill_changed)
        form_layout.addRow("技力消耗:", self.cost_edit)
        
        # 技能效果
        self.effect_edit = DetailedTextEdit("技能效果")
        self.effect_edit.setFixedHeight(80)
        self.effect_edit.setPlaceholderText("技能效果描述...")
        self.effect_edit.textChanged.connect(self._on_skill_changed)
        form_layout.addRow("效果:", self.effect_edit)
        
        layout.addLayout(form_layout)
    
    def _load_skill_data(self, skill_data: Dict[str, str]):
        """加载技能数据"""
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
    
    def update_index(self, new_index: int):
        """更新技能索引"""
        self.skill_index = new_index
        # 更新标题显示
        header_layout = self.layout().itemAt(0).layout()
        title_label = header_layout.itemAt(0).widget()
        title_label.setText(f"技能 {new_index + 1}")


class SkillEditorPanel(QWidget):
    """技能编辑面板"""
    
    skillChanged = Signal(int, dict)  # 技能变化信号
    skillsUpdated = Signal(list)      # 技能列表更新信号
    talentsChanged = Signal(str)      # 天赋变化信号
    
    def __init__(self, card_model: Optional[CardModel] = None, parent=None):
        super().__init__(parent)
        self.card_model = card_model
        self.skill_widgets: List[SkillEditWidget] = []
        self._create_ui()
        if card_model:
            self._connect_signals()
            self._refresh_from_model()
    
    def _create_ui(self):
        """创建用户界面"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 技能区域标题和按钮
        skills_header_layout = QHBoxLayout()
        
        skills_title = QLabel("技能设定")
        skills_title.setStyleSheet("font-weight: bold; font-size: 16px; color: #2c3e50;")
        
        self.add_skill_btn = QPushButton("+ 添加技能")
        self.add_skill_btn.setStyleSheet(ADD_BUTTON_STYLE)
        self.add_skill_btn.clicked.connect(self._add_skill)
        
        skills_header_layout.addWidget(skills_title)
        skills_header_layout.addStretch()
        skills_header_layout.addWidget(self.add_skill_btn)
        layout.addLayout(skills_header_layout)
        
        # 技能说明
        info_label = QLabel("可动态添加或删除技能，空技能将被自动过滤")
        info_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # 技能列表容器
        self.skills_layout = QVBoxLayout()
        layout.addLayout(self.skills_layout)
        
        # 天赋能力区域
        talents_header = QLabel("天赋 & 能力")
        talents_header.setStyleSheet("font-weight: bold; font-size: 16px; color: #2c3e50; margin-top: 20px;")
        layout.addWidget(talents_header)
        
        self.talents_edit = DetailedTextEdit("天赋 & 能力")
        self.talents_edit.setFixedHeight(150)
        self.talents_edit.setPlaceholderText("描述敌人的天赋和特殊能力...")
        self.talents_edit.setStyleSheet(TEXT_EDIT_STYLE)
        layout.addWidget(self.talents_edit)
        
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
        self.talents_edit.textChanged.connect(
            lambda: self.talentsChanged.emit(self.talents_edit.toPlainText()))
    
    def _add_skill(self):
        """添加新技能"""
        skill_index = len(self.skill_widgets)
        skill_widget = SkillEditWidget(skill_index)
        skill_widget.skillChanged.connect(self._on_skill_changed)
        skill_widget.removeRequested.connect(self._remove_skill)
        
        self.skill_widgets.append(skill_widget)
        self.skills_layout.addWidget(skill_widget)
        
        # 重新索引所有技能
        self._reindex_skills()
    
    def _remove_skill(self, skill_index: int):
        """删除技能"""
        if 0 <= skill_index < len(self.skill_widgets):
            skill_widget = self.skill_widgets[skill_index]
            self.skills_layout.removeWidget(skill_widget)
            skill_widget.deleteLater()
            self.skill_widgets.pop(skill_index)
            
            # 重新索引所有技能
            self._reindex_skills()
            
            # 更新数据模型
            self._update_all_skills()
    
    def _reindex_skills(self):
        """重新索引所有技能组件"""
        for i, skill_widget in enumerate(self.skill_widgets):
            skill_widget.update_index(i)
    
    def _update_all_skills(self):
        """更新所有技能到数据模型"""
        skills_data = []
        for skill_widget in self.skill_widgets:
            skill_data = skill_widget.get_skill_data()
            # 只添加非空技能
            if any(skill_data.values()):
                skills_data.append(skill_data)
        self.skillsUpdated.emit(skills_data)

    def _on_skill_changed(self, skill_index: int, skill_data: Dict[str, str]):
        """技能变化处理"""
        self.skillChanged.emit(skill_index, skill_data)
    
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
        
        # 首先清空现有的技能组件
        for skill_widget in self.skill_widgets:
            self.skills_layout.removeWidget(skill_widget)
            skill_widget.deleteLater()
        self.skill_widgets.clear()
        
        # 根据数据重新创建技能组件
        for i in range(len(data.skills)):
            skill_widget = SkillEditWidget(i, data.skills[i])
            skill_widget.skillChanged.connect(self._on_skill_changed)
            skill_widget.removeRequested.connect(self._remove_skill)
            
            self.skill_widgets.append(skill_widget)
            self.skills_layout.addWidget(skill_widget)
        
        # 天赋能力
        self.talents_edit.setPlainText(data.talents_abilities)
    
    def refresh_from_model(self):
        """外部调用刷新接口"""
        self._refresh_from_model()