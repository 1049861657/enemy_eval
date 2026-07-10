"""
属性面板样式定义 - 集中管理所有QSS样式
"""

# 标签页样式
TAB_WIDGET_STYLE = """
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
"""

# 数值输入框样式（无加减按钮）
SPINBOX_NO_BUTTONS_STYLE = """
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

# 复选框样式
CHECKBOX_STYLE = """
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

# 星级评价组件样式
STAR_RATING_STYLE = """
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
"""

# 技能编辑组件样式
SKILL_EDIT_STYLE = """
SkillEditWidget {
    background-color: #f8f9fa;
    border-radius: 8px;
    padding: 8px;
    margin: 4px 0px;
}
"""

# 删除按钮样式
REMOVE_BUTTON_STYLE = """
QPushButton {
    background-color: #e74c3c;
    border: none;
    border-radius: 12px;
}
QPushButton:hover {
    background-color: #c0392b;
}
"""

# 添加按钮样式
ADD_BUTTON_STYLE = """
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
"""

# 文本输入框样式
TEXT_EDIT_STYLE = """
QTextEdit {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 8px;
    font-size: 13px;
}
"""

# 评价框架样式
RATING_GROUP_STYLE = """
QFrame { 
    border: 2px solid #4A90E2; 
    border-radius: 8px; 
    margin: 4px; 
    background: white;
}
"""

DESCRIPTION_GROUP_STYLE = """
QFrame { 
    border: 2px solid #7B68EE; 
    border-radius: 8px; 
    margin: 4px; 
    background: white;
}
"""

COMMENT_GROUP_STYLE = """
QFrame { 
    border: 2px solid #FF6B6B; 
    border-radius: 8px; 
    margin: 4px; 
    background: white;
}
"""

# 标题栏样式
RATING_TITLE_STYLE = """
QLabel { 
    color: white; 
    font-weight: bold; 
    font-size: 16px; 
    padding: 12px; 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4A90E2, stop:1 #357ABD);
    border: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
"""

DESCRIPTION_TITLE_STYLE = """
QLabel { 
    color: white; 
    font-weight: bold; 
    font-size: 16px; 
    padding: 12px; 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7B68EE, stop:1 #6A5ACD);
    border: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
"""

COMMENT_TITLE_STYLE = """
QLabel { 
    color: white; 
    font-weight: bold; 
    font-size: 16px; 
    padding: 12px; 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF6B6B, stop:1 #FF5252);
    border: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
"""

# 内容区域样式
CONTENT_AREA_STYLE = """
QWidget {
    background: white;
    padding: 15px;
    border: none;
}
"""

# 评级标签样式
RATING_LABEL_STYLE = """
QLabel {
    font-weight: bold;
    color: #2c3e50;
    font-size: 14px;
}
"""

RATING_SETTINGS_BTN_STYLE = """
QPushButton {
    background: rgba(255, 255, 255, 0.18);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.45);
    border-radius: 16px;
    font-size: 16px;
    font-weight: bold;
}
QPushButton:hover {
    background: rgba(255, 255, 255, 0.32);
}
"""

RATING_DONE_BTN_STYLE = """
QPushButton {
    background: #ffffff;
    color: #357ABD;
    border: none;
    border-radius: 6px;
    padding: 4px 12px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover {
    background: #e8f1fb;
}
"""

RATING_ADD_BTN_STYLE = """
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
QPushButton:disabled {
    background-color: #95a5a6;
}
"""

RATING_REMOVE_BTN_STYLE = """
QPushButton {
    background-color: #e74c3c;
    color: white;
    border: none;
    border-radius: 14px;
    font-size: 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #c0392b;
}
"""

RATING_NAME_EDIT_STYLE = """
QLineEdit {
    font-weight: bold;
    color: #2c3e50;
    font-size: 14px;
    border: 1px solid #4A90E2;
    border-radius: 4px;
    padding: 2px 6px;
    background: #f8fbff;
}
"""


# 详细文本编辑框样式
DETAILED_TEXT_EDIT_STYLE = """
QTextEdit { 
    border: 1px solid #ccc; 
    border-radius: 6px; 
    padding: 8px; 
    font-size: 13px;
    background-color: white;
}
"""