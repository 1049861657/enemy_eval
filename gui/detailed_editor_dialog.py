"""
详细编辑对话框 - 为文本框提供最佳编辑体验
"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
                               QPushButton, QLabel, QWidget)
from .styles import (
    DETAILED_EDITOR_DIALOG_STYLE, DETAILED_EDITOR_TITLE_STYLE, DETAILED_EDITOR_HINT_STYLE,
    DETAILED_EDITOR_CONTAINER_STYLE, DETAILED_EDITOR_TEXT_STYLE,
    DETAILED_EDITOR_CHAR_COUNT_STYLE, DETAILED_EDITOR_CANCEL_STYLE, DETAILED_EDITOR_SAVE_STYLE,
)


class DetailedEditorDialog(QDialog):
    """详细文本编辑对话框"""
    
    textChanged = Signal(str)  # 文本变化信号
    
    def __init__(self, title: str = "详细编辑", 
                 initial_text: str = "", 
                 placeholder: str = "",
                 parent=None):
        super().__init__(parent)
        self.initial_text = initial_text
        self.current_text = initial_text
        
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(800, 600)
        self.setMinimumSize(600, 400)
        
        self._create_ui(placeholder)
        self._setup_shortcuts()
        self._load_text(initial_text)
    
    def _create_ui(self, placeholder: str):
        """创建用户界面"""
        # 设置窗口样式
        self.setStyleSheet(DETAILED_EDITOR_DIALOG_STYLE)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 20, 24, 20)
        
        # 简洁标题区域
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("✨ 详细编辑模式")
        title_label.setStyleSheet(DETAILED_EDITOR_TITLE_STYLE)
        
        hint_label = QLabel("Ctrl+Enter保存 • Esc取消")
        hint_label.setStyleSheet(DETAILED_EDITOR_HINT_STYLE)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(hint_label)
        layout.addLayout(title_layout)
        
        # 文本编辑区域 - 现代化设计
        editor_container = QWidget()
        editor_container.setStyleSheet(DETAILED_EDITOR_CONTAINER_STYLE)
        
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(16, 16, 16, 16)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(placeholder)
        
        # 设置现代化字体
        font = QFont("Microsoft YaHei UI", 11)
        font.setWeight(QFont.Weight.Normal)
        self.text_edit.setFont(font)
        
        self.text_edit.setStyleSheet(DETAILED_EDITOR_TEXT_STYLE)
        
        # 连接文本变化信号
        self.text_edit.textChanged.connect(self._on_text_changed)
        
        editor_layout.addWidget(self.text_edit)
        layout.addWidget(editor_container)
        
        # 按钮区域 - 现代化设计
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(12)
        
        # 字数统计标签
        self.char_count_label = QLabel("字数: 0")
        self.char_count_label.setStyleSheet(DETAILED_EDITOR_CHAR_COUNT_STYLE)
        
        button_layout.addWidget(self.char_count_label)
        button_layout.addStretch()
        
        # 取消按钮 - 现代化设计
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(80, 36)
        cancel_btn.setStyleSheet(DETAILED_EDITOR_CANCEL_STYLE)
        cancel_btn.clicked.connect(self.reject)
        
        # 保存按钮 - 现代化设计
        save_btn = QPushButton("保存")
        save_btn.setFixedSize(80, 36)
        save_btn.setStyleSheet(DETAILED_EDITOR_SAVE_STYLE)
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addWidget(button_container)
        
        # 设置焦点到文本编辑器
        self.text_edit.setFocus()
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+Enter 保存
        save_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        save_shortcut.activated.connect(self.accept)
        
        # Esc 取消
        cancel_shortcut = QShortcut(QKeySequence("Esc"), self)
        cancel_shortcut.activated.connect(self.reject)
    
    def _load_text(self, text: str):
        """加载文本内容"""
        self.text_edit.setPlainText(text)
        self.current_text = text
        self._update_char_count()
        
        # 将光标移动到文本末尾
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)
    
    def _on_text_changed(self):
        """文本变化处理"""
        self.current_text = self.text_edit.toPlainText()
        self._update_char_count()
        self.textChanged.emit(self.current_text)
    
    def _update_char_count(self):
        """更新字数统计"""
        text = self.current_text.strip()
        char_count = len(text)
        self.char_count_label.setText(f"字数: {char_count}")
    
    def get_text(self) -> str:
        """获取当前文本"""
        return self.current_text
    
    def set_text(self, text: str):
        """设置文本内容"""
        self._load_text(text)
    
    @staticmethod
    def edit_text(title: str, initial_text: str = "", 
                  placeholder: str = "", parent=None) -> tuple[bool, str]:
        """
        静态方法，打开编辑对话框并返回结果
        
        Returns:
            tuple[bool, str]: (是否确认, 文本内容)
        """
        dialog = DetailedEditorDialog(title, initial_text, placeholder, parent)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            return True, dialog.get_text()
        else:
            return False, initial_text