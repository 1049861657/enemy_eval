"""预览组件 QSS 样式定义。"""

from .colors import PRIMARY_COLOR, PRIMARY_HOVER, DISABLED_BG, ERROR_COLOR

PREVIEW_EXPORT_BTN_STYLE = f"""
QPushButton {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {PRIMARY_HOVER};
}}
QPushButton:disabled {{
    background-color: {DISABLED_BG};
}}
"""

PREVIEW_ERROR_LABEL_STYLE = f"color: {ERROR_COLOR}; font-size: 12px;"
PREVIEW_INFO_LABEL_STYLE = "color: #666; font-size: 12px;"
