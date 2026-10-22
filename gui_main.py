#!/usr/bin/env python3
"""GUI 入口：依赖自检 → 启动封面 → 注册 QML 根目录与静态资源 → 主窗口与事件循环。"""

import importlib
import sys
import time
from pathlib import Path

import structlog
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QIcon, QPixmap
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen

sys.path.insert(0, str(Path(__file__).parent))

from utils.app.identity import APP_AUTHOR, APP_NAME
from utils.app.logging import setup_logging
from utils.app.version import get_app_build_time, get_app_version
from utils.app.resources import resource_manager

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
    cover_path = resource_manager.get_pic_path("封面.png")
    pixmap = QPixmap(cover_path)
    
    # 等比缩放至 800×600 上限
    pixmap = pixmap.scaled(800, 600, Qt.AspectRatioMode.KeepAspectRatio, 
                          Qt.TransformationMode.SmoothTransformation)
    
    splash = QSplashScreen(pixmap)
    splash.show()
    
    return splash


def register_bundled_font() -> None:
    """把随包中文字体注册给 Qt，供界面字体回退栈使用。"""
    font_path = resource_manager.get_resource_path(
        "resource/fonts/HarmonyOS_Sans_SC_Regular.ttf"
    )
    font_id = QFontDatabase.addApplicationFont(font_path)
    logger = structlog.get_logger(__name__)
    if font_id < 0:
        logger.warning("随包字体注册失败", font_path=font_path)
        return
    logger.info(
        "已注册随包字体",
        families=QFontDatabase.applicationFontFamilies(font_id),
    )


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
    started = time.perf_counter()
    missing_deps = check_dependencies()
    if missing_deps:
        return show_dependency_error(missing_deps)
    
    # 必须在创建 QApplication 前选择 Qt Quick Controls 风格。
    QQuickStyle.setStyle("FluentWinUI3")

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_manager.get_resource_path("resource/icon.png")))
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(get_app_version())
    app.setOrganizationName(APP_AUTHOR)
    setup_logging()
    register_bundled_font()
    
    splash = create_splash_screen()
    app.processEvents()
    
    try:
        main_window = MainWindow()
        workspace = getattr(main_window, "workspace", None)
        if workspace is not None and workspace.status() == QQuickWidget.Status.Ready:
            structlog.get_logger(__name__).info(
                "QML 就绪",
                elapsed_ms=round((time.perf_counter() - started) * 1000),
                version=get_app_version(),
                built_at=get_app_build_time() or "",
            )

        main_window.show()
        splash.finish(main_window)

        return app.exec()
        
    except Exception as e:
        splash.close()
        
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