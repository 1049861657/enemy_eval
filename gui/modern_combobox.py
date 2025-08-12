"""
现代化下拉框组件 - 完美的通用下拉框解决方案
作者: Claude 4.0 sonnet
"""

from enum import Enum
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor
from PySide6.QtWidgets import (QComboBox, QWidget, QStyledItemDelegate, QStyleOptionViewItem,
                               QListView)


class ComboBoxTheme(Enum):
    """下拉框主题枚举"""
    DEFAULT = "default"           # 默认主题


class ComboBoxSize(Enum):
    """下拉框尺寸枚举"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class ModernItemDelegate(QStyledItemDelegate):
    """现代化列表项委托"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_color = QColor(236, 245, 255)
        self._selected_color = QColor(64, 158, 255)
        self._text_color = QColor(48, 49, 51)
        self._selected_text_color = QColor(255, 255, 255)
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """自定义绘制项目"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 计算绘制区域
        rect = option.rect.adjusted(6, 2, -6, -2)
        
        # 绘制背景
        if option.state & QStyleOptionViewItem.State.Selected:
            painter.setBrush(QBrush(self._selected_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QPen(self._selected_text_color))
        elif option.state & QStyleOptionViewItem.State.MouseOver:
            painter.setBrush(QBrush(self._hover_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QPen(self._text_color))
        else:
            painter.setPen(QPen(self._text_color))
        
        # 绘制文本
        text_rect = rect.adjusted(12, 0, -12, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, 
                        index.data(Qt.ItemDataRole.DisplayRole))


class ModernComboBox(QComboBox):
    """现代化下拉框组件"""
    
    # 自定义信号
    itemHovered = Signal(int)  # 项目悬停信号
    dropdownOpened = Signal()  # 下拉列表打开信号
    dropdownClosed = Signal()  # 下拉列表关闭信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 尺寸配置
        self._size = ComboBoxSize.MEDIUM
        
        # 初始化设置
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """初始化用户界面"""
        # 设置基础属性
        self.setMinimumHeight(self._get_height_for_size())
        self.setMouseTracking(True)
        
        # 设置自定义委托
        self.setItemDelegate(ModernItemDelegate(self))
        
        # 配置下拉视图
        self.setMaxVisibleItems(10)
        list_view = QListView()
        list_view.setMouseTracking(True)
        self.setView(list_view)
        
        # 应用默认样式
        self._apply_theme()
    
    def _connect_signals(self):
        """连接信号和槽"""
        self.activated.connect(self._on_item_activated)
        self.highlighted.connect(self.itemHovered.emit)
    
    def _get_height_for_size(self) -> int:
        """根据尺寸获取高度"""
        size_heights = {
            ComboBoxSize.SMALL: 32,
            ComboBoxSize.MEDIUM: 40,
            ComboBoxSize.LARGE: 48
        }
        return size_heights.get(self._size, 40)
    
    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(self._get_default_style())
    
    def _get_base_style(self) -> str:
        """获取基础样式"""
        height = self._get_height_for_size()
        return f"""
            QComboBox {{
                font-size: 14px;
                min-height: {height - 16}px;
                outline: none;
            }}
            
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border: none;
                background: transparent;
            }}
            
            QComboBox::down-arrow {{
                width: 0;
                height: 0;
                border: 6px solid transparent;
                margin: 0;
                top: 1px;
            }}
            
            QComboBox QAbstractItemView {{
                outline: none;
                padding: 4px 0;
                margin-top: 2px;
            }}
        """
    
    def _get_default_style(self) -> str:
        """默认主题样式 - 与其他输入框保持一致"""
        return self._get_base_style() + """
            QComboBox {
                background-color: white;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                color: #303133;
                padding: 5px 30px 5px 12px;
            }
            
            QComboBox:hover {
                border-color: #409eff;
            }
            
            QComboBox:focus {
                border-color: #409eff;
            }
            
            QComboBox:on {
                border-color: #409eff;
            }
            
            QComboBox::drop-down {
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            
            QComboBox::down-arrow {
                border-top: 6px solid #909399;
            }
            
            QComboBox:hover::down-arrow {
                border-top-color: #409eff;
            }
            
            QComboBox:on::down-arrow {
                border-top-color: #409eff;
            }
            
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                outline: none;
            }
            
            QComboBox QAbstractItemView::item {
                height: 30px;
                padding: 0 12px;
                margin: 1px 4px;
                border-radius: 3px;
            }
            
            QComboBox QAbstractItemView::item:hover {
                background-color: #f5f7fa;
                color: #303133;
            }
            
            QComboBox QAbstractItemView::item:selected {
                background-color: #409eff;
                color: white;
            }
        """
    
    
    def _on_item_activated(self, index: int):
        """项目激活处理"""
        pass
    
    def set_size(self, size: ComboBoxSize):
        """设置尺寸"""
        self._size = size
        self.setMinimumHeight(self._get_height_for_size())
        self._apply_theme()
    
    def showPopup(self):
        """显示下拉列表"""
        super().showPopup()
        self.dropdownOpened.emit()
    
    def hidePopup(self):
        """隐藏下拉列表"""
        super().hidePopup()
        self.dropdownClosed.emit()


# 便捷函数

def create_combo_box(items: List[str] = None, 
                    size: ComboBoxSize = ComboBoxSize.MEDIUM,
                    parent: QWidget = None) -> ModernComboBox:
    """快速创建现代化下拉框"""
    combo = ModernComboBox(parent)
    combo.set_size(size)
    
    if items:
        combo.addItems(items)
    
    return combo


