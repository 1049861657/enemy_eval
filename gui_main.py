#!/usr/bin/env python3
"""
敌人评价卡片实时编辑器 - GUI入口程序
使用PySide6构建的现代化桌面应用程序
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QPen, QBrush, QFont

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from gui.main_window import MainWindow
except ImportError as e:
    print(f"导入GUI模块失败: {e}")
    print("请确保已安装PySide6: pip install PySide6")
    sys.exit(1)


def create_splash_screen():
    """创建启动画面"""
    # 创建一个简单的启动画面
    pixmap = QPixmap(400, 300)
    pixmap.fill(Qt.white)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # 绘制背景渐变
    gradient_rect = pixmap.rect()
    painter.setBrush(QBrush(Qt.blue, Qt.LinearGradientPattern))
    painter.setPen(Qt.NoPen)
    painter.drawRect(gradient_rect)
    
    # 绘制标题
    painter.setPen(QPen(Qt.white))
    title_font = QFont("Arial", 20, QFont.Bold)
    painter.setFont(title_font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "敌人评价卡片编辑器\\n\\n正在启动...")
    
    painter.end()
    
    splash = QSplashScreen(pixmap)
    splash.show()
    
    return splash


def check_dependencies():
    """检查依赖项"""
    missing_deps = []
    
    try:
        import skia
    except ImportError:
        missing_deps.append("skia-python")
    
    try:
        import pydantic
    except ImportError:
        missing_deps.append("pydantic")
    
    try:
        import PIL
    except ImportError:
        missing_deps.append("Pillow")
    
    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        import rich
    except ImportError:
        missing_deps.append("rich")
    
    return missing_deps


def show_dependency_error(missing_deps):
    """显示依赖项缺失错误"""
    app = QApplication(sys.argv)
    
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("依赖项缺失")
    msg.setText("缺少必要的依赖项，程序无法启动。")
    
    detail_text = "缺少以下依赖项:\\n\\n"
    for dep in missing_deps:
        detail_text += f"• {dep}\\n"
    
    detail_text += "\\n请运行以下命令安装：\\n"
    detail_text += f"pip install {' '.join(missing_deps)}"
    
    msg.setDetailedText(detail_text)
    msg.setStandardButtons(QMessageBox.Ok)
    
    msg.exec()
    return False


def main():
    """主函数"""
    # 检查依赖项
    missing_deps = check_dependencies()
    if missing_deps:
        return show_dependency_error(missing_deps)
    
    # 创建应用程序
    app = QApplication(sys.argv)
    app.setApplicationName("敌人评价卡片编辑器")
    app.setApplicationVersion("1.0")
    app.setApplicationDisplayName("敌人评价卡片实时编辑器")
    app.setOrganizationName("Enemy Eval Team")
    
    # 设置应用程序样式
    app.setStyle('Fusion')  # 使用现代化样式
    
    # 显示启动画面
    splash = create_splash_screen()
    app.processEvents()
    
    try:
        # 模拟加载时间
        QTimer.singleShot(1500, splash.close)
        
        # 创建主窗口
        main_window = MainWindow()
        
        # 1.5秒后显示主窗口
        def show_main_window():
            splash.finish(main_window)
            main_window.show()
        
        QTimer.singleShot(1500, show_main_window)
        
        # 运行事件循环
        return app.exec()
        
    except Exception as e:
        splash.close()
        
        # 显示错误对话框
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("启动失败")
        msg.setText("程序启动时发生错误。")
        msg.setDetailedText(f"错误详情:\\n{str(e)}")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
        
        return 1


if __name__ == "__main__":
    sys.exit(main())