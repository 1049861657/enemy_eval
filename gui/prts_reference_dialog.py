"""
PRTS参考对话框 - 美化的敌人查询界面
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton)

from utils import resource_manager


class PrtsReferenceDialog(QDialog):
    """美化的PRTS参考对话框"""
    
    enemy_name_entered = Signal(str)  # 发送敌人名称的信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI布局"""
        self.setModal(True)
        self.setFixedSize(380, 140)
        # 设置窗口标志，防止继承父窗口标题
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)
        
        # 顶部区域：输入框和提示按钮
        input_area = QHBoxLayout()
        input_area.setSpacing(15)
        
        # 输入框
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入敌人名称...")
        self.name_input.setObjectName("name_input")
        self.name_input.setMinimumHeight(40)
        
        # 提示按钮
        self.help_button = QPushButton()
        self.help_button.setFixedSize(32, 32)
        self.help_button.setObjectName("help_button")
        self.help_button.setToolTip(
            "当前仅支持返回主要属性以及头像。\n"
            "异常抗性，技能天赋等请自行复制粘贴。"
        )
        # 设置图标
        icon_path = resource_manager.get_icon_path("icons8-tooltip-100.png")
        icon = QIcon(icon_path)
        self.help_button.setIcon(icon)
        self.help_button.setIconSize(self.help_button.size() * 0.8)
        
        input_area.addWidget(self.name_input)
        input_area.addWidget(self.help_button)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.setMinimumSize(80, 36)
        
        # 确定按钮
        self.ok_button = QPushButton("查询")
        self.ok_button.setObjectName("ok_button")
        self.ok_button.setMinimumSize(80, 36)
        self.ok_button.setDefault(True)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        # 添加到主布局
        main_layout.addLayout(input_area)
        main_layout.addLayout(button_layout)
    
    def _apply_styles(self):
        """应用样式表"""
        self.setStyleSheet("""
            /* 对话框主体样式 */
            QDialog {
                background-color: #ffffff;
                border: 1px solid #dcdfe6;
                border-radius: 6px;
            }
            
            /* 输入框 */
            #name_input {
                background-color: white;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                padding: 12px 16px;
                font-size: 14px;
                color: #303133;
            }
            
            #name_input:focus {
                border-color: #409eff;
                outline: none;
            }
            
            #name_input:hover {
                border-color: #c0c4cc;
            }
            
            /* 提示按钮 */
            #help_button {
                background: transparent;
                border: none;
                padding: 4px;
                border-radius: 16px;
                outline: none;
            }
            
            #help_button:hover {
                background-color: #f0f9ff;
                transform: scale(1.05);
            }
            
            #help_button:pressed {
                background-color: #e0f3ff;
                transform: scale(0.98);
            }
            
            /* 取消按钮 */
            #cancel_button {
                background-color: #f5f5f5;
                color: #606266;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
            }
            
            #cancel_button:hover {
                background-color: #ecf5ff;
                border-color: #409eff;
                color: #409eff;
            }
            
            #cancel_button:pressed {
                background-color: #d9ecff;
            }
            
            /* 确定按钮 */
            #ok_button {
                background-color: #409eff;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
            }
            
            #ok_button:hover {
                background-color: #66b1ff;
                transform: translateY(-1px);
            }
            
            #ok_button:pressed {
                background-color: #3a8ee6;
                transform: translateY(0px);
            }
            
            #ok_button:disabled {
                background-color: #c0c4cc;
                color: #ffffff;
                transform: none;
            }
        """)
    
    def _connect_signals(self):
        """连接信号槽"""
        self.ok_button.clicked.connect(self._handle_ok_clicked)
        self.cancel_button.clicked.connect(self.reject)
        self.name_input.returnPressed.connect(self._handle_ok_clicked)
        self.name_input.textChanged.connect(self._update_ok_button_state)
        
        # 初始化按钮状态
        self._update_ok_button_state()
    
    def _update_ok_button_state(self):
        """更新确定按钮状态"""
        has_text = bool(self.name_input.text().strip())
        self.ok_button.setEnabled(has_text)
    
    def _handle_ok_clicked(self):
        """处理确定按钮点击"""
        enemy_name = self.name_input.text().strip()
        if enemy_name:
            self.enemy_name_entered.emit(enemy_name)
            self.accept()
    
    def showEvent(self, event):
        """显示事件 - 设置焦点"""
        super().showEvent(event)
        self.name_input.setFocus()
        self.name_input.selectAll()
    
    def get_enemy_name(self):
        """获取输入的敌人名称"""
        return self.name_input.text().strip()
    
    @classmethod
    def get_enemy_name_input(cls, parent=None, title=""):
        """静态方法 - 获取敌人名称输入"""
        dialog = cls(parent)
        dialog.setWindowTitle(title)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_enemy_name(), True
        return "", False