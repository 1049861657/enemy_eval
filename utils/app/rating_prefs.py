"""新建卡片的评价维度模板：偏好里的 rating_names 字段。

契约：模板合法性一律由 models.RatingSchema 校验；写盘只经 utils/app/settings.py::update_settings，
失败抛 FileOperationError（界面据此提示）。core 不得导入本模块。
"""

from __future__ import annotations

from models import RatingSchema

from .settings import load_app_settings, update_settings


def load_rating_schema(*, force_reload: bool = False) -> RatingSchema:
    """加载新建卡片用的维度模板。"""
    return RatingSchema(names=load_app_settings(force_reload=force_reload).rating_names)


def save_rating_schema(schema: RatingSchema) -> RatingSchema:
    """校验维度模板并写入偏好 JSON，保留其余字段。"""
    validated = RatingSchema.model_validate(schema)
    update_settings(rating_names=list(validated.names))
    return validated


def get_rating_names() -> list[str]:
    """新建卡片使用的维度名称。"""
    return list(load_app_settings().rating_names)
