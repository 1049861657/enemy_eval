"""全局评价标准（维度名称/数量）的读写；与敌人分数分离持久化。"""

from __future__ import annotations

import json
import logging
import threading

from PySide6.QtCore import QSettings
from models import RatingSchema, default_rating_scores

logger = logging.getLogger(__name__)

_ORGANIZATION_NAME = "Enemy Eval Team"
_APPLICATION_NAME = "敌人评价卡片编辑器"
_SCHEMA_KEY = "rating_schema/names"
_lock = threading.RLock()
_cached: RatingSchema | None = None


def _settings() -> QSettings:
    """获取应用级用户设置存储（Windows 为当前用户注册表）。"""
    return QSettings(
        QSettings.Format.NativeFormat,
        QSettings.Scope.UserScope,
        _ORGANIZATION_NAME,
        _APPLICATION_NAME,
    )


def load_rating_schema(*, force_reload: bool = False) -> RatingSchema:
    """加载全局评价标准；缺失或损坏时回退默认三维。"""
    global _cached
    with _lock:
        if _cached is not None and not force_reload:
            return _cached

        raw = _settings().value(_SCHEMA_KEY)
        if raw is not None:
            try:
                _cached = RatingSchema.model_validate_json(str(raw))
                return _cached
            except Exception as e:
                logger.warning("评价标准配置损坏，使用默认值: %s", e)
        _cached = RatingSchema()
        return _cached


def save_rating_schema(schema: RatingSchema) -> RatingSchema:
    """校验并写入应用级用户设置，更新内存缓存。"""
    global _cached
    validated = RatingSchema.model_validate(schema)
    with _lock:
        settings = _settings()
        settings.setValue(
            _SCHEMA_KEY,
            json.dumps(validated.model_dump(), ensure_ascii=False, separators=(",", ":")),
        )
        settings.sync()
        if settings.status() != QSettings.Status.NoError:
            raise RuntimeError("保存评价标准失败")
        _cached = validated
    return validated


def get_rating_names() -> list[str]:
    return list(load_rating_schema().names)


def default_scores_for_current_schema() -> list[int]:
    return default_rating_scores(len(load_rating_schema().names))
