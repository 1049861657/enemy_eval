"""应用偏好：JSON 文件的读取、容错与落盘，不含领域语义。

唯一落盘点：`update_settings`（失败抛 FileOperationError）与 `_write_updates`（吞掉并记日志）。
领域封装见同包的 rating_prefs / ai_prefs / render_prefs，它们只调用本模块，不各自建立缓存。
偏好文件缺失、损坏或字段非法一律回落默认值，不抛给调用方。core 不得导入本模块。
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Literal

import structlog
from platformdirs import user_config_path
from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from models import DEFAULT_RATING_NAMES, RatingSchema

from ..errors import FileOperationError
from .identity import APP_AUTHOR, APP_NAME

logger = structlog.get_logger(__name__)

_SETTINGS_FILENAME = "app_settings.json"
_MAX_RECENT_FILES = 8
_lock = threading.RLock()
_cached: AppSettings | None = None


def settings_file_path() -> Path:
    """用户级偏好 JSON；测试可 monkeypatch 本函数以注入临时目录。"""
    return user_config_path(APP_NAME, appauthor=APP_AUTHOR) / _SETTINGS_FILENAME


class _TolerantJsonConfigSettingsSource(JsonConfigSettingsSource):
    """偏好文件缺失或损坏时按「该文件不存在」处理。

    基类在构造期解析文件，解析错误会在建模型阶段抛 ValidationError；本类把损坏吸收在
    读取层，上层只需再处理「JSON 合法但内容不合法」。
    """

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        try:
            data = super()._read_file(file_path)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as error:
            logger.warning(
                "评价偏好文件无法解析，已忽略",
                path=str(file_path),
                error=str(error),
            )
            return {}
        if not isinstance(data, dict):
            logger.warning("评价偏好文件内容不是对象，已忽略", path=str(file_path))
            return {}
        return data


class AppSettings(BaseSettings):
    """应用偏好。rating_names 是新建卡片的维度模板，合法性由 RatingSchema 校验；ai_* 三项为空即未配置；proxy_mode 默认直连。"""

    model_config = SettingsConfigDict(extra="ignore", json_file_encoding="utf-8")

    rating_names: list[str] = Field(default_factory=lambda: list(DEFAULT_RATING_NAMES))
    rating_radar: bool = False
    recent_files: list[str] = Field(default_factory=list)
    update_check_enabled: bool = True
    update_check_last_ts: float = 0.0
    update_check_block_until: float = 0.0
    update_check_etag: str = ""
    update_seen_tag: str = ""
    update_seen_url: str = ""
    update_check_skip_tag: str = ""
    proxy_mode: Literal["system", "none"] = "none"
    ai_base_url: str = ""
    ai_model: str = ""
    ai_api_key: str = ""
    ai_persona: str = ""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        del env_settings, dotenv_settings, file_secret_settings
        return (
            init_settings,
            _TolerantJsonConfigSettingsSource(
                settings_cls,
                json_file=settings_file_path(),
                json_file_encoding="utf-8",
            ),
        )


def _default_settings() -> AppSettings:
    return AppSettings.model_validate(
        {"rating_names": list(DEFAULT_RATING_NAMES), "rating_radar": False}
    )


def _read_settings() -> AppSettings:
    path = settings_file_path()
    if not path.is_file():
        logger.warning("评价偏好文件不存在，使用默认值", path=str(path))
        return _default_settings()
    try:
        loaded = AppSettings()
        RatingSchema(names=loaded.rating_names)
        return loaded
    except Exception as error:
        logger.warning("评价偏好损坏，使用默认值", error=str(error))
        return _default_settings()


def _persist(settings: AppSettings) -> None:
    path = settings_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            settings.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as error:
        raise FileOperationError(f"保存评价偏好失败: {error}") from error


def _cloned(current: AppSettings, **updates: Any) -> AppSettings:
    """在既有偏好上改若干字段，其余原样保留。"""
    data = current.model_dump()
    data.update(updates)
    return AppSettings.model_validate(data)


def update_settings(**updates: Any) -> AppSettings:
    """在缓存或盘上偏好上改若干字段并落盘，返回新偏好。

    唯一的落盘点。写盘失败抛 FileOperationError 且内存缓存保持原状——吞掉还是抛给界面由调用方定。
    """
    global _cached
    with _lock:
        current = _cached if _cached is not None else _read_settings()
        settings = _cloned(current, **updates)
        _persist(settings)
        _cached = settings
        return settings


def try_update_settings(**updates: Any) -> None:
    """写入偏好字段；写盘失败只记日志（不抛），内存保持原状。"""
    try:
        update_settings(**updates)
    except FileOperationError as error:
        logger.warning("偏好未写入，已忽略", error=str(error))


def _replace_recent_files(entries: list[str]) -> None:
    """写入新的最近列表；失败只记日志并保留原内存状态。"""
    try:
        update_settings(recent_files=entries)
    except FileOperationError as error:
        logger.warning("最近列表未写入，已忽略", error=str(error))


def load_app_settings(*, force_reload: bool = False) -> AppSettings:
    """加载偏好；缺失或损坏时回退默认三维且雷达关闭。"""
    global _cached
    with _lock:
        if _cached is not None and not force_reload:
            return _cached
        _cached = _read_settings()
        return _cached


def recent_files() -> list[str]:
    """最近打开或保存过的配置绝对路径，最近的在前；返回副本。"""
    return list(load_app_settings().recent_files)


def remember_recent_file(path: str) -> None:
    """把配置路径记为最近一项；重复项提到最前，超出上限截断，写盘失败只记日志。"""
    absolute = os.path.abspath(path)
    key = os.path.normcase(absolute)
    with _lock:
        current = load_app_settings()
        others = [
            entry
            for entry in current.recent_files
            if os.path.normcase(os.path.abspath(entry)) != key
        ]
        _replace_recent_files([absolute, *others][:_MAX_RECENT_FILES])


def remove_recent_file(path: str) -> None:
    """从最近列表移除指定配置；不在列表中则不动。"""
    key = os.path.normcase(os.path.abspath(path))
    with _lock:
        current = load_app_settings()
        entries = [
            entry
            for entry in current.recent_files
            if os.path.normcase(os.path.abspath(entry)) != key
        ]
        if entries != list(current.recent_files):
            _replace_recent_files(entries)


def clear_recent_files() -> None:
    """清空最近列表。"""
    with _lock:
        if load_app_settings().recent_files:
            _replace_recent_files([])
