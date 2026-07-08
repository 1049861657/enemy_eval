"""对话框 QSS 样式定义。

覆盖 PrtsReferenceDialog 与 DetailedEditorDialog 的全部内联样式。
"""

from .colors import (
    PRIMARY_COLOR, PRIMARY_HOVER, PRIMARY_PRESSED, DISABLED_BG, DISABLED_FG,
    ACTION_PRIMARY_TOP, ACTION_PRIMARY_BOT,
    ACTION_HOVER_TOP, ACTION_HOVER_BOT,
    ACTION_PRESSED_TOP, ACTION_PRESSED_BOT,
    BORDER_DEFAULT, BORDER_HOVER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_PLACEHOLDER,
    BG_CANVAS, BG_CANVAS_END, BG_WHITE, BG_SUBTLE, BG_CANCEL,
    BG_CANCEL_HOVER, BG_CANCEL_PRESSED,
)

# ── PrtsReferenceDialog ───────────────────────────────────────────────────────

PRTS_DIALOG_STYLE = f"""
QDialog {{
    background-color: {BG_WHITE};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
}}
#name_input {{
    background-color: {BG_WHITE};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 4px;
    padding: 12px 16px;
    font-size: 14px;
    color: {TEXT_PRIMARY};
}}
#name_input:focus {{
    border-color: {PRIMARY_COLOR};
    outline: none;
}}
#name_input:hover {{
    border-color: {BORDER_HOVER};
}}
#help_button {{
    background: transparent;
    border: none;
    padding: 4px;
    border-radius: 16px;
    outline: none;
}}
#help_button:hover {{
    background-color: #f0f9ff;
}}
#help_button:pressed {{
    background-color: #e0f3ff;
}}
#cancel_button {{
    background-color: {BG_CANCEL};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
}}
#cancel_button:hover {{
    background-color: {BG_CANCEL_HOVER};
    border-color: {PRIMARY_COLOR};
    color: {PRIMARY_COLOR};
}}
#cancel_button:pressed {{
    background-color: {BG_CANCEL_PRESSED};
}}
#ok_button {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
}}
#ok_button:hover {{
    background-color: {PRIMARY_HOVER};
}}
#ok_button:pressed {{
    background-color: {PRIMARY_PRESSED};
}}
#ok_button:disabled {{
    background-color: {DISABLED_BG};
    color: {DISABLED_FG};
}}
"""

# ── DetailedEditorDialog ──────────────────────────────────────────────────────

DETAILED_EDITOR_DIALOG_STYLE = f"""
QDialog {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {BG_CANVAS}, stop:1 {BG_CANVAS_END});
}}
"""

DETAILED_EDITOR_TITLE_STYLE = f"""
color: #475569;
font-weight: 600;
font-size: 16px;
font-family: 'Microsoft YaHei UI', sans-serif;
"""

DETAILED_EDITOR_HINT_STYLE = f"""
color: {TEXT_PLACEHOLDER};
font-size: 12px;
font-weight: 400;
"""

DETAILED_EDITOR_CONTAINER_STYLE = f"""
QWidget {{
    background-color: {BG_WHITE};
    border-radius: 12px;
    border: 1px solid {BG_CANVAS_END};
}}
"""

DETAILED_EDITOR_TEXT_STYLE = f"""
QTextEdit {{
    border: none;
    background-color: transparent;
    selection-background-color: {ACTION_PRIMARY_TOP};
    selection-color: white;
    line-height: 1.6;
    color: #1e293b;
}}
QTextEdit:focus {{
    outline: none;
}}
QScrollBar:vertical {{
    background: {BG_SUBTLE};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: #94a3b8;
}}
"""

DETAILED_EDITOR_CHAR_COUNT_STYLE = f"""
color: #64748b;
font-size: 12px;
font-weight: 400;
"""

DETAILED_EDITOR_CANCEL_STYLE = f"""
QPushButton {{
    background-color: {BG_SUBTLE};
    color: #64748b;
    border: 1px solid {BG_CANVAS_END};
    border-radius: 8px;
    font-weight: 500;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {BG_CANVAS_END};
    border-color: #cbd5e1;
}}
QPushButton:pressed {{
    background-color: #cbd5e1;
}}
"""

DETAILED_EDITOR_SAVE_STYLE = f"""
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {ACTION_PRIMARY_TOP}, stop:1 {ACTION_PRIMARY_BOT});
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {ACTION_HOVER_TOP}, stop:1 {ACTION_HOVER_BOT});
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {ACTION_PRESSED_TOP}, stop:1 {ACTION_PRESSED_BOT});
}}
"""
