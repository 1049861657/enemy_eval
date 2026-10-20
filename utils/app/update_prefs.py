"""版本检查的偏好字段：自动检查开关、上次检查时间、退避截止、已见版本与 ETag。

契约：只写 `update_check_*` / `update_seen_*` 字段；写盘失败只记日志（界面不需要知道），
落盘经 utils/app/settings.py::try_update_settings。响应解析与版本比较见同包 update_check.py。
"""

from __future__ import annotations

from .settings import try_update_settings


def set_update_check_enabled(enabled: bool) -> None:
    """写入启动时自动检查开关。"""
    try_update_settings(update_check_enabled=bool(enabled))


def mark_update_checked(timestamp: float) -> None:
    """记下一次问到明确结果的时间。"""
    try_update_settings(update_check_last_ts=float(timestamp))


def set_update_block_until(timestamp: float) -> None:
    """记下失败退避的截止时间。"""
    try_update_settings(update_check_block_until=float(timestamp))


def set_update_seen(tag: str, url: str, etag: str) -> None:
    """记下一次 200 见到的正式版和 ETag。"""
    try_update_settings(
        update_seen_tag=tag,
        update_seen_url=url,
        update_check_etag=etag,
    )


def clear_update_seen() -> None:
    """清掉已见版本、链接和 ETag。不改忽略版本。"""
    try_update_settings(update_seen_tag="", update_seen_url="", update_check_etag="")


def set_update_skip_tag(tag: str) -> None:
    """忽略这个版本。已见版本和 ETag 保留。"""
    try_update_settings(update_check_skip_tag=tag)
