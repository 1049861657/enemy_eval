"""应用外壳域：身份、版本、更新检查开关、应用图标路径。"""

from __future__ import annotations

from PySide6.QtCore import QUrl

from utils.app.identity import APP_NAME, APP_SUMMARY
from utils.app.resources import resource_manager
from utils.app.settings import load_app_settings
from utils.app.update_prefs import set_update_check_enabled
from utils.app.version import get_app_build_time, get_app_version


def app_name() -> str:
    return APP_NAME


def app_summary() -> str:
    """一句话简介（关于窗口用）。"""
    return APP_SUMMARY


def app_icon_url() -> str:
    """应用图标在打包资源里的绝对 URL；供 QML Image 直接使用。"""
    return QUrl.fromLocalFile(
        resource_manager.get_resource_path("resource/icon.png")
    ).toString()


def app_version() -> str:
    """当前版本号（已安装分发版 / 冻结制品 / pyproject.toml 三者之一）。"""
    return get_app_version()


def app_build_time() -> str:
    """构建时间文案；源码运行时为空串。"""
    return get_app_build_time() or ""


def update_check_enabled() -> bool:
    """启动时是否自动检查更新。"""
    return load_app_settings().update_check_enabled


def save_update_check_enabled(enabled: bool) -> None:
    """写入自动检查开关。"""
    set_update_check_enabled(enabled)
