"""卡片画布与主题相关配置（预留）。"""

from pydantic import BaseModel, Field


class CardStyle(BaseModel):
    """卡片样式配置"""

    width: int = Field(default=800, description="画布宽度")
    height: int = Field(default=600, description="画布高度")

    background_color: str = Field(default="#f0f0f0", description="背景色")
    primary_color: str = Field(default="#333333", description="主要文字颜色")
    accent_color: str = Field(default="#ff6b6b", description="强调色")

    font_size_title: int = Field(default=24, description="标题字体大小")
    font_size_normal: int = Field(default=16, description="正常字体大小")
    font_size_small: int = Field(default=12, description="小字体大小")

    padding: int = Field(default=20, description="边距")
    avatar_size: int = Field(default=120, description="头像尺寸")
    star_size: int = Field(default=20, description="星星尺寸")
