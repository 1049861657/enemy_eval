"""评价展示偏好 → models.RenderOptions 的唯一装配点。

契约：core 不读偏好存储，渲染选项只由 GUI/CLI 经 current_render_options() 传入；
维度名称在敌人数据上，不在此处。写盘只经 utils/app/settings.py::update_settings。
"""

from __future__ import annotations

from models import RenderOptions

from .settings import load_app_settings, update_settings


def is_rating_radar(*, force_reload: bool = False) -> bool:
    """评价区是否绘制雷达图；默认记分板。"""
    return load_app_settings(force_reload=force_reload).rating_radar


def set_rating_radar(enabled: bool) -> bool:
    """写入评价展示方式并更新缓存。"""
    value = bool(enabled)
    update_settings(rating_radar=value)
    return value


def current_render_options() -> RenderOptions:
    """从当前偏好组装雷达开关；维度名称在敌人数据上。core 不得自行调用。"""
    return RenderOptions(rating_radar=load_app_settings().rating_radar)
