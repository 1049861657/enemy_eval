"""网络偏好：代理模式（跟随系统 / 不使用代理）。

契约：只读写 `proxy_mode` 字段；写盘失败只记日志。系统代理如何解析见
`utils/net/proxy.py`，本模块不接触环境变量或注册表。
"""

from __future__ import annotations

from typing import Literal

from .settings import load_app_settings, try_update_settings

ProxyMode = Literal["system", "none"]


def proxy_mode() -> ProxyMode:
    """当前代理模式；缺失或损坏时按默认值 `none`。"""
    return load_app_settings().proxy_mode


def set_proxy_mode(mode: ProxyMode) -> None:
    """写入代理模式；写盘失败只记日志。"""
    try_update_settings(proxy_mode=mode)
