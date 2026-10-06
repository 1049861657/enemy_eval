"""一次绘制所需的非敌人输入；由 GUI/CLI 在调用前组装。"""

from pydantic import BaseModel, ConfigDict


class RenderOptions(BaseModel):
    """渲染侧只消费本对象。评价维度在敌人数据上；此处只带展示开关。"""

    model_config = ConfigDict(frozen=True)

    rating_radar: bool = False
