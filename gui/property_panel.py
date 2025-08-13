"""
属性编辑面板 - 敌人属性的交互式编辑界面
"""

from typing import Dict

from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
                               QComboBox, QTextEdit, QLabel, QPushButton,
                               QFileDialog, QCheckBox, QScrollArea, QFrame, QGridLayout)
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QIcon

from .card_model import CardModel


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
        
        # 美化样式
        self.setStyleSheet("""
            StarRatingWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                border-radius: 15px;
                padding: 3px;
            }
            StarRatingWidget:hover {
                border-color: #4A90E2;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #f0f8ff, stop:1 #e6f3ff);
            }
        """)
    
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
        import math
        
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
        
        from PySide6.QtGui import QPolygon
        from PySide6.QtCore import QPoint
        
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


class SkillEditWidget(QWidget):
    """技能编辑组件"""
    
    skillChanged = Signal(int, dict)  # 技能变化信号
    removeRequested = Signal(int)     # 请求删除信号
    
    def __init__(self, skill_index: int, skill_data: Dict[str, str] = None):
        super().__init__()
        self.skill_index = skill_index
        
        # 使用更简洁的样式
        self.setStyleSheet("""
            SkillEditWidget {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 8px;
                margin: 4px 0px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # 添加标题栏（技能序号和删除按钮）
        header_layout = QHBoxLayout()
        skill_title = QLabel(f"技能 {skill_index + 1}")
        skill_title.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 14px;")
        
        self.remove_btn = QPushButton()
        self.remove_btn.setFixedSize(24, 24)
        
        # 设置删除图标
        icon_path = "resource/ico/icons8-delete-96.png"
        self.remove_btn.setIcon(QIcon(icon_path))
        self.remove_btn.setIconSize(self.remove_btn.size())  # 图标填满按钮
        
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
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
        self.cost_edit.setPlaceholderText("可选，如: 10 (空白显示斜线)")
        self.cost_edit.textChanged.connect(self._on_skill_changed)
        form_layout.addRow("技力消耗:", self.cost_edit)
        
        # 技能效果
        self.effect_edit = QTextEdit()
        self.effect_edit.setMinimumHeight(30)
        self.effect_edit.setPlaceholderText("技能效果描述...")
        self.effect_edit.textChanged.connect(self._on_skill_changed)
        form_layout.addRow("效果:", self.effect_edit)
        
        layout.addLayout(form_layout)
        
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
        
        # 美化标签页样式
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: white;
                margin-top: 2px;
            }
            
            QTabWidget::tab-bar {
                alignment: left;
                left: 5px;
            }
            
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                min-width: 40px;
                padding: 8px 10px;
                margin-right: 1px;
                font-weight: 500;
                font-size: 13px;
                color: #495057;
            }
            
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border-color: #4A90E2;
                border-bottom: 2px solid #4A90E2;
                color: #2c3e50;
                font-weight: 600;
            }
            
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f8ff, stop:1 #e6f3ff);
                border-color: #4A90E2;
                color: #2c3e50;
            }
            
            QTabBar::tab:first {
                margin-left: 5px;
            }
        """)
        
        layout.addWidget(self.tab_widget)
        
        # 基础信息标签页
        self._create_basic_tab()
        
        # 战斗属性标签页
        self._create_combat_tab()
        
        # 异常抗性标签页
        self._create_resistance_tab()
        
        # 技能标签页
        self._create_skills_tab()
        
        # 评价标签页（包含评级和简评）
        self._create_rating_tab()
    
    def _create_basic_tab(self):
        """创建基础信息标签页"""
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
        self.attack_type_combo.addItems(['近战', '远程', '近战/远程'])
        layout.addRow("攻击方式:", self.attack_type_combo)
        
        # 伤害类型
        self.damage_type_combo = QComboBox()
        self.damage_type_combo.addItems(['物理', '法术'])
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
        self.category_combo.addItems(['感染生物', '无人机', '萨卡兹', '宿主', '海怪', '法术造物', '源石造物', '化物', '机械', '野生动物', '坍缩体', '其他'])
        self.category_combo.setCurrentText('其他')
        layout.addRow("种类:", self.category_combo)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.tab_widget.addTab(scroll_area, "基础信息")
    
    def _create_combat_tab(self):
        """创建战斗属性标签页"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QFormLayout(scroll_widget)
        
        # 去掉加减按钮的样式
        no_buttons_style = """
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: right;
                width: 0px;
                height: 0px;
                border: none;
                background: none;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: right;
                width: 0px;
                height: 0px;
                border: none;
                background: none;
            }
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                width: 0px;
                height: 0px;
            }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                width: 0px;
                height: 0px;
            }
            QSpinBox, QDoubleSpinBox {
                padding-right: 3px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
        """
        
        # 生命相关
        self.max_hp_spin = QSpinBox()
        self.max_hp_spin.setRange(1, 999999)
        self.max_hp_spin.setValue(1000)
        self.max_hp_spin.setStyleSheet(no_buttons_style)
        layout.addRow("最大生命值:", self.max_hp_spin)
        
        self.hp_recovery_spin = QDoubleSpinBox()
        self.hp_recovery_spin.setRange(0, 10000)
        self.hp_recovery_spin.setDecimals(1)
        self.hp_recovery_spin.setStyleSheet(no_buttons_style)
        layout.addRow("生命自回速度:", self.hp_recovery_spin)
        
        # 攻击相关
        self.attack_spin = QSpinBox()
        self.attack_spin.setRange(0, 999999)
        self.attack_spin.setValue(100)
        self.attack_spin.setStyleSheet(no_buttons_style)
        layout.addRow("攻击力:", self.attack_spin)
        
        self.attack_interval_spin = QDoubleSpinBox()
        self.attack_interval_spin.setRange(0.1, 10.0)
        self.attack_interval_spin.setDecimals(1)
        self.attack_interval_spin.setValue(2.0)
        self.attack_interval_spin.setStyleSheet(no_buttons_style)
        layout.addRow("攻击间隔:", self.attack_interval_spin)
        
        self.attack_range_spin = QDoubleSpinBox()
        self.attack_range_spin.setRange(0.0, 10.0)
        self.attack_range_spin.setDecimals(1)
        self.attack_range_spin.setValue(1.0)
        self.attack_range_spin.setStyleSheet(no_buttons_style)
        layout.addRow("攻击范围半径:", self.attack_range_spin)
        
        # 防御相关
        self.defense_spin = QSpinBox()
        self.defense_spin.setRange(0, 999999)
        self.defense_spin.setValue(50)
        self.defense_spin.setStyleSheet(no_buttons_style)
        layout.addRow("防御力:", self.defense_spin)
        
        self.magic_resistance_spin = QSpinBox()
        self.magic_resistance_spin.setRange(0, 100)
        self.magic_resistance_spin.setValue(10)
        self.magic_resistance_spin.setStyleSheet(no_buttons_style)
        layout.addRow("法术抗性:", self.magic_resistance_spin)
        
        self.damage_resistance_spin = QSpinBox()
        self.damage_resistance_spin.setRange(0, 100)
        self.damage_resistance_spin.setStyleSheet(no_buttons_style)
        layout.addRow("损伤抗性:", self.damage_resistance_spin)
        
        self.element_resistance_spin = QSpinBox()
        self.element_resistance_spin.setRange(0, 100)
        self.element_resistance_spin.setStyleSheet(no_buttons_style)
        layout.addRow("元素抗性:", self.element_resistance_spin)
        
        # 移动相关
        self.move_speed_spin = QDoubleSpinBox()
        self.move_speed_spin.setRange(0.1, 5.0)
        self.move_speed_spin.setDecimals(2)
        self.move_speed_spin.setValue(1.0)
        self.move_speed_spin.setStyleSheet(no_buttons_style)
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
        self.tab_widget.addTab(scroll_area, "战斗属性")
    
    def _create_resistance_tab(self):
        """创建异常抗性标签页"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 异常抗性说明
        info_label = QLabel("选中表示对该异常状态有抗性")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)
        
        # 异常抗性复选框 - 使用网格布局
        self.resistance_checkboxes = {}
        resistances = ['冻结', '沉默', '晕眩', '沉睡', '浮空', '战栗', '恐惧','麻痹', '诱导', ]
        
        # 创建网格布局容器
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(12)  # 设置间距
        grid_layout.setContentsMargins(20, 10, 20, 10)  # 设置边距
        
        # 复选框样式
        checkbox_style = """
            QCheckBox {
                font-size: 14px;
                font-weight: 500;
                color: #2c3e50;
                spacing: 8px;
                padding: 8px 12px;
                border-radius: 6px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
            }
            QCheckBox:hover {
                background-color: #e3f2fd;
                border-color: #4A90E2;
            }
            QCheckBox:checked {
                background-color: #e8f5e8;
                border-color: #4caf50;
                color: #2e7d32;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 2px solid #dee2e6;
                background-color: white;
            }
            QCheckBox::indicator:hover {
                border-color: #4A90E2;
            }
            QCheckBox::indicator:checked {
                background-color: #4caf50;
                border-color: #4caf50;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }
        """
        
        # 按3列布局排列复选框
        for i, resistance in enumerate(resistances):
            checkbox = QCheckBox(resistance)
            checkbox.setStyleSheet(checkbox_style)
            self.resistance_checkboxes[resistance] = checkbox
            
            row = i // 3
            col = i % 3
            grid_layout.addWidget(checkbox, row, col)
        
        layout.addWidget(grid_widget)
        
        layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.tab_widget.addTab(scroll_area, "异常抗性")
    
    def _create_skills_tab(self):
        """创建技能标签页"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 技能区域标题和按钮
        skills_header_layout = QHBoxLayout()
        
        skills_title = QLabel("技能设定")
        skills_title.setStyleSheet("font-weight: bold; font-size: 16px; color: #2c3e50;")
        
        self.add_skill_btn = QPushButton("+ 添加技能")
        self.add_skill_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
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
        
        # 初始化时不添加任何技能，默认为空
        
        # 天赋能力区域
        talents_header = QLabel("天赋 & 能力")
        talents_header.setStyleSheet("font-weight: bold; font-size: 16px; color: #2c3e50; margin-top: 20px;")
        layout.addWidget(talents_header)
        
        self.talents_edit = QTextEdit()
        self.talents_edit.setMaximumHeight(120)
        self.talents_edit.setPlaceholderText("描述敌人的天赋和特殊能力...")
        self.talents_edit.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.talents_edit)
        
        layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.tab_widget.addTab(scroll_area, "技能天赋")
    
    def _create_rating_tab(self):
        """创建评价标签页（包含评级和简评）"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(8)  # 减少组件间距
        
        # 更有特色的样式定义 - 优化标题内容分离
        rating_group_style = """
        QFrame { 
            border: 2px solid #4A90E2; 
            border-radius: 8px; 
            margin: 4px; 
            background: white;
        }"""
        
        description_group_style = """
        QFrame { 
            border: 2px solid #7B68EE; 
            border-radius: 8px; 
            margin: 4px; 
            background: white;
        }"""
        
        comment_group_style = """
        QFrame { 
            border: 2px solid #FF6B6B; 
            border-radius: 8px; 
            margin: 4px; 
            background: white;
        }"""
        
        # 标题栏样式定义
        rating_title_style = """
        QLabel { 
            color: white; 
            font-weight: bold; 
            font-size: 16px; 
            padding: 12px; 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4A90E2, stop:1 #357ABD);
            border: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }"""
        
        description_title_style = """
        QLabel { 
            color: white; 
            font-weight: bold; 
            font-size: 16px; 
            padding: 12px; 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7B68EE, stop:1 #6A5ACD);
            border: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }"""
        
        comment_title_style = """
        QLabel { 
            color: white; 
            font-weight: bold; 
            font-size: 16px; 
            padding: 12px; 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF6B6B, stop:1 #FF5252);
            border: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }"""
        
        # 内容区域样式
        content_area_style = """
        QWidget {
            background: white;
            padding: 15px;
            border: none;
        }"""
        
        # === 评级部分 ===
        rating_group = QFrame()
        rating_group.setFrameStyle(QFrame.Shape.Box)
        rating_group.setStyleSheet(rating_group_style)
        rating_main_layout = QVBoxLayout(rating_group)
        rating_main_layout.setSpacing(0)
        rating_main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 评级标题栏
        rating_title_label = QLabel("📊 评级 (各项评级范围: 1-5星)")
        rating_title_label.setStyleSheet(rating_title_style)
        rating_main_layout.addWidget(rating_title_label)
        
        # 评级内容区域
        rating_content_widget = QWidget()
        rating_content_widget.setStyleSheet(content_area_style)
        rating_content_layout = QVBoxLayout(rating_content_widget)
        rating_content_layout.setContentsMargins(15, 15, 15, 15)
        
        # 评级项目 - 简洁的星级评价布局
        rating_items_layout = QVBoxLayout()
        rating_items_layout.setSpacing(16)  # 增加评级项之间的间距
        
        # 评级项标签样式
        rating_label_style = """
        QLabel {
            font-weight: bold;
            color: #2c3e50;
            font-size: 14px;
        }
        """
        
        # 对策度评级
        hostility_layout = QHBoxLayout()
        hostility_layout.setSpacing(8)  # 减少间距让星级靠近文字
        
        hostility_label = QLabel("🎯 对策度")
        hostility_label.setStyleSheet(rating_label_style)
        hostility_label.setFixedWidth(110)  # 拓宽文字区域
        self.hostility_rating = StarRatingWidget(5, 3)
        
        hostility_layout.addWidget(hostility_label)
        hostility_layout.addWidget(self.hostility_rating)
        hostility_layout.addStretch()
        
        # 创新度评级
        innovation_layout = QHBoxLayout()
        innovation_layout.setSpacing(8)  # 减少间距让星级靠近文字
        
        innovation_label = QLabel("💡 创新度")
        innovation_label.setStyleSheet(rating_label_style)
        innovation_label.setFixedWidth(110)  # 拓宽文字区域
        self.innovation_rating = StarRatingWidget(5, 3)
        
        innovation_layout.addWidget(innovation_label)
        innovation_layout.addWidget(self.innovation_rating)
        innovation_layout.addStretch()
        
        # 威胁度评级
        threat_layout = QHBoxLayout()
        threat_layout.setSpacing(8)  # 减少间距让星级靠近文字
        
        threat_label = QLabel("⚡ 威胁度")
        threat_label.setStyleSheet(rating_label_style)
        threat_label.setFixedWidth(110)  # 拓宽文字区域
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
        description_group.setStyleSheet(description_group_style)
        description_main_layout = QVBoxLayout(description_group)
        description_main_layout.setSpacing(0)
        description_main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 敌人描述标题栏
        description_title_label = QLabel("📋 敌人描述")
        description_title_label.setStyleSheet(description_title_style)
        description_main_layout.addWidget(description_title_label)
        
        # 敌人描述内容区域
        description_content_widget = QWidget()
        description_content_widget.setStyleSheet(content_area_style)
        description_content_layout = QVBoxLayout(description_content_widget)
        description_content_layout.setContentsMargins(15, 15, 15, 15)
        
        # 简要描述 - 增加默认高度
        self.brief_description_edit = QTextEdit()
        self.brief_description_edit.setMinimumHeight(120)  # 增加默认高度
        self.brief_description_edit.setMaximumHeight(160)
        self.brief_description_edit.setPlaceholderText("敌人的基本特点和能力描述...")
        self.brief_description_edit.setStyleSheet("""
            QTextEdit { 
                border: 1px solid #ccc; 
                border-radius: 6px; 
                padding: 8px; 
                font-size: 13px;
                background-color: white;
            }
        """)
        description_content_layout.addWidget(self.brief_description_edit)
        description_main_layout.addWidget(description_content_widget)
        
        layout.addWidget(description_group)
        
        # === 简要评价部分 ===
        comment_group = QFrame()
        comment_group.setFrameStyle(QFrame.Shape.Box)
        comment_group.setStyleSheet(comment_group_style)
        comment_main_layout = QVBoxLayout(comment_group)
        comment_main_layout.setSpacing(0)
        comment_main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 简评标题栏
        comment_title_label = QLabel("💬 简要评价")
        comment_title_label.setStyleSheet(comment_title_style)
        comment_main_layout.addWidget(comment_title_label)
        
        # 简评内容区域
        comment_content_widget = QWidget()
        comment_content_widget.setStyleSheet(content_area_style)
        comment_content_layout = QVBoxLayout(comment_content_widget)
        comment_content_layout.setContentsMargins(15, 15, 15, 15)
        
        # 简评内容 - 增加默认高度
        self.brief_comment_edit = QTextEdit()
        self.brief_comment_edit.setMinimumHeight(120)  # 增加默认高度
        self.brief_comment_edit.setMaximumHeight(160)
        self.brief_comment_edit.setPlaceholderText("对敌人的整体评价...")
        self.brief_comment_edit.setStyleSheet("""
            QTextEdit { 
                border: 1px solid #ccc; 
                border-radius: 6px; 
                padding: 8px; 
                font-size: 13px;
                background-color: white;
            }
        """)
        comment_content_layout.addWidget(self.brief_comment_edit)
        comment_main_layout.addWidget(comment_content_widget)
        
        layout.addWidget(comment_group)
        layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.tab_widget.addTab(scroll_area, "评价")
    
    
    def _connect_signals(self):
        """连接信号与槽"""
        # 基础信息
        self.name_edit.textChanged.connect(lambda: self._update_property('name', self.name_edit.text()))
        self.grade_combo.currentTextChanged.connect(lambda: self._update_property('grade', self.grade_combo.currentText()))
        self.avatar_edit.textChanged.connect(lambda: self._update_property('avatar_path', self.avatar_edit.text()))
        self.attack_type_combo.currentTextChanged.connect(self._on_attack_type_changed)
        self.damage_type_combo.currentTextChanged.connect(lambda: self._update_property('damage_type', self.damage_type_combo.currentText()))
        self.action_type_combo.currentTextChanged.connect(lambda: self._update_property('action_type', self.action_type_combo.currentText()))
        self.position_combo.currentTextChanged.connect(lambda: self._update_property('position', self.position_combo.currentText()))
        self.category_combo.currentTextChanged.connect(lambda: self._update_property('category', self.category_combo.currentText()))
        
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
        self.hostility_rating.valueChanged.connect(lambda value: self._update_property('hostility_rating', value))
        self.innovation_rating.valueChanged.connect(lambda value: self._update_property('innovation_rating', value))
        self.threat_rating.valueChanged.connect(lambda value: self._update_property('threat_rating', value))
        
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
    
    def _on_attack_type_changed(self):
        """攻击方式变化处理"""
        attack_type = self.attack_type_combo.currentText()
        
        if attack_type == "近战":
            # 近战时设为0且禁用编辑
            self.attack_range_spin.setValue(0.0)
            self.attack_range_spin.setEnabled(False)
        else:
            # 非近战时启用编辑
            self.attack_range_spin.setEnabled(True)
            if self.attack_range_spin.value() == 0.0:
                self.attack_range_spin.setValue(1.0)  # 恢复默认值
        
        # 更新数据模型
        self._update_property('attack_type', attack_type)
    
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
        # 移除指定的技能组件，允许删空所有技能
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
            skill_widget.skill_index = i
            # 更新标题显示
            header_layout = skill_widget.layout().itemAt(0).layout()
            title_label = header_layout.itemAt(0).widget()
            title_label.setText(f"技能 {i + 1}")
    
    def _update_all_skills(self):
        """更新所有技能到数据模型"""
        skills_data = []
        for skill_widget in self.skill_widgets:
            skill_data = skill_widget.get_skill_data()
            # 只添加非空技能
            if any(skill_data.values()):
                skills_data.append(skill_data)
        self.card_model.update_property('skills', skills_data)

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
        self.category_combo.setCurrentText(data.category)
        
        # 战斗属性
        self.max_hp_spin.setValue(data.max_hp)
        self.hp_recovery_spin.setValue(data.hp_recovery_speed)
        self.attack_spin.setValue(data.attack)
        self.attack_interval_spin.setValue(data.attack_interval)
        self.attack_range_spin.setValue(data.attack_range_radius)
        
        # 应用攻击方式的控制逻辑
        if data.attack_type == "近战":
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
        
        # 异常抗性
        for name, checkbox in self.resistance_checkboxes.items():
            is_resistant = data.abnormal_resistances.get(name, 0.0) > 0
            checkbox.setChecked(is_resistant)
        
        # 技能 - 动态调整技能数量
        # 首先清空现有的技能组件
        for skill_widget in self.skill_widgets:
            self.skills_layout.removeWidget(skill_widget)
            skill_widget.deleteLater()
        self.skill_widgets.clear()
        
        # 根据数据重新创建技能组件
        for i in range(len(data.skills)):
            skill_widget = SkillEditWidget(i)
            skill_widget.skillChanged.connect(self._on_skill_changed)
            skill_widget.removeRequested.connect(self._remove_skill)
            
            if i < len(data.skills):
                skill_data = data.skills[i]
                skill_widget.name_edit.setText(skill_data.get('名称', ''))
                skill_widget.cooldown_edit.setText(skill_data.get('冷却时间', ''))
                skill_widget.cost_edit.setText(skill_data.get('技力消耗', ''))
                skill_widget.effect_edit.setPlainText(skill_data.get('效果', ''))
            
            self.skill_widgets.append(skill_widget)
            self.skills_layout.addWidget(skill_widget)
        
        # 天赋能力
        self.talents_edit.setPlainText(data.talents_abilities)
        
        # 评级
        self.hostility_rating.setValue(data.hostility_rating)
        self.innovation_rating.setValue(data.innovation_rating)
        self.threat_rating.setValue(data.threat_rating)
        
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