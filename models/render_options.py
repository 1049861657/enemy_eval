"""一次绘制所需的非敌人输入；由 GUI/CLI 在调用前组装。"""

from pydantic import BaseModel, ConfigDict, Field


class RenderOptions(BaseModel):
    """渲染侧只消费本对象，不读全局评价标准或 Qt 偏好。"""

    model_config = ConfigDict(frozen=True)

    rating_names: list[str] = Field(default_factory=list)
    rating_radar: bool = False
