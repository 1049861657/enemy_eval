"""应用偏好：评价维度与雷达开关，JSON 持久化。core 不得导入本模块。"""

from __future__ import annotations

import threading
from pathlib import Path

import structlog
from platformdirs import user_config_path
from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from models import DEFAULT_RATING_NAMES, RatingSchema, RenderOptions, default_rating_scores

from .error_handler import FileOperationError

logger = structlog.get_logger(__name__)

_APP_NAME = "敌人评价卡片编辑器"
_APP_AUTHOR = "Enemy Eval Team"
_SETTINGS_FILENAME = "app_settings.json"
_lock = threading.RLock()
_cached: AppSettings | None = None


def settings_file_path() -> Path:
    """用户级偏好 JSON；测试可 monkeypatch 本函数以注入临时目录。"""
    return user_config_path(_APP_NAME, appauthor=_APP_AUTHOR) / _SETTINGS_FILENAME


class AppSettings(BaseSettings):
    """评价偏好。维度合法性由 RatingSchema 校验，本模型只承载字段。"""

    model_config = SettingsConfigDict(extra="ignore", json_file_encoding="utf-8")

    rating_names: list[str] = Field(default_factory=lambda: list(DEFAULT_RATING_NAMES))
    rating_radar: bool = False

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
            JsonConfigSettingsSource(
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


def load_app_settings(*, force_reload: bool = False) -> AppSettings:
    """加载偏好；缺失或损坏时回退默认三维且雷达关闭。"""
    global _cached
    with _lock:
        if _cached is not None and not force_reload:
            return _cached
        _cached = _read_settings()
        return _cached


def load_rating_schema(*, force_reload: bool = False) -> RatingSchema:
    """加载全局评价标准。"""
    return RatingSchema(names=load_app_settings(force_reload=force_reload).rating_names)


def save_rating_schema(schema: RatingSchema) -> RatingSchema:
    """校验维度并写入偏好 JSON，保留当前雷达开关。"""
    global _cached
    validated = RatingSchema.model_validate(schema)
    with _lock:
        current = _cached if _cached is not None else _read_settings()
        settings = AppSettings.model_validate(
            {
                "rating_names": list(validated.names),
                "rating_radar": current.rating_radar,
            }
        )
        _persist(settings)
        _cached = settings
    return validated


def get_rating_names() -> list[str]:
    return list(load_app_settings().rating_names)


def default_scores_for_current_schema() -> list[int]:
    return default_rating_scores(len(load_app_settings().rating_names))


def is_rating_radar(*, force_reload: bool = False) -> bool:
    """评价区是否绘制雷达图；默认记分板。"""
    return load_app_settings(force_reload=force_reload).rating_radar


def set_rating_radar(enabled: bool) -> bool:
    """写入评价展示方式并更新缓存。"""
    global _cached
    value = bool(enabled)
    with _lock:
        current = _cached if _cached is not None else _read_settings()
        settings = AppSettings.model_validate(
            {
                "rating_names": list(current.rating_names),
                "rating_radar": value,
            }
        )
        _persist(settings)
        _cached = settings
    return value


def current_render_options() -> RenderOptions:
    """从当前偏好组装一次绘制输入；core 不得自行调用。"""
    settings = load_app_settings()
    return RenderOptions(
        rating_names=list(settings.rating_names),
        rating_radar=settings.rating_radar,
    )
