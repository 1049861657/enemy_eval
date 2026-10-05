#!/usr/bin/env python3
"""
敌人评价卡片实时编辑器 - GUI入口程序
使用PySide6构建的现代化桌面应用程序
"""

import importlib
import sys
import time
from pathlib import Path

import structlog
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.app_logging import setup_logging
from utils.app_version import get_app_build_time, get_app_version
from utils.resource_manager import resource_manager

try:
    from gui.main_window import MainWindow
except ImportError as e:
    setup_logging()
    structlog.get_logger(__name__).error(
        "导入GUI模块失败",
        error=str(e),
        hint="请在项目根目录运行 uv sync",
    )
    sys.exit(1)


def create_splash_screen():
    """创建启动画面"""
    cover_path = resource_manager.get_pic_path("封面.png")
    pixmap = QPixmap(cover_path)
    
    # 等比缩放至 800×600 上限
    pixmap = pixmap.scaled(800, 600, Qt.AspectRatioMode.KeepAspectRatio, 
                          Qt.TransformationMode.SmoothTransformation)
    
    splash = QSplashScreen(pixmap)
    splash.show()
    
    return splash


def check_dependencies() -> list[str]:
    """检查启动所需的渲染与 GUI 依赖。"""
    required = (
        ("skia", "skia-python"),
        ("pydantic", "pydantic"),
        ("PySide6", "PySide6"),
        ("httpx", "httpx"),
    )
    missing_deps: list[str] = []
    for module_name, package_name in required:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing_deps.append(package_name)
    return missing_deps


def show_dependency_error(missing_deps):
    """显示依赖项缺失错误"""
    app = QApplication(sys.argv)
    
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle("依赖项缺失")
    msg.setText("缺少必要的依赖项，程序无法启动。")
    
    detail_text = "缺少以下依赖项:\n\n"
    for dep in missing_deps:
        detail_text += f"• {dep}\n"
    
    detail_text += "\n请在项目根目录运行：\n"
    detail_text += "uv sync"
    
    msg.setDetailedText(detail_text)
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    
    msg.exec()
    return False


def main():
    """主函数"""
    started = time.perf_counter()
    # 检查依赖项
    missing_deps = check_dependencies()
    if missing_deps:
        return show_dependency_error(missing_deps)
    
    # 必须在创建 QApplication 前选择 Qt Quick Controls 风格。
    QQuickStyle.setStyle("FluentWinUI3")

    # 创建应用程序
    app = QApplication(sys.argv)
    app.setApplicationName("敌人评价卡片编辑器")
    app.setApplicationVersion(get_app_version())
    app.setOrganizationName("Enemy Eval Team")
    setup_logging()
    
    # 显示启动画面
    splash = create_splash_screen()
    app.processEvents()
    
    try:
        # 创建主窗口
        main_window = MainWindow()
        workspace = getattr(main_window, "workspace", None)
        if workspace is not None and workspace.status() == QQuickWidget.Status.Ready:
            structlog.get_logger(__name__).info(
                "QML 就绪",
                elapsed_ms=round((time.perf_counter() - started) * 1000),
                version=get_app_version(),
                built_at=get_app_build_time() or "",
            )

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
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("启动失败")
        msg.setText("程序启动时发生错误。")
        msg.setDetailedText(f"错误详情:\n{str(e)}")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        
        return 1


if __name__ == "__main__":
    sys.exit(main())