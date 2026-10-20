"""渲染配置：画布尺寸与各类缓存容量。core 内部常量，不来自偏好文件。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RenderConfig:
    """渲染配置参数。

    - `width` / `height`：卡片画布逻辑尺寸（像素，1 单位 = 1 像素）；长卡以 `height` 为基准增高。
    - `canvas_pool_size`：画布池容量（张）；池满后新建临时 Surface，不入池。
    - `text_cache_size`：文本布局缓存条数上限，超出按最旧时间戳淘汰。
    - `image_cache_size`：全局图像缓存条数上限（`LRUCache` maxsize），超限淘汰最久未用项。
    - `cache_expire_seconds`：文本布局缓存有效期（秒）。
    """

    width: int = 1950
    height: int = 1500

    canvas_pool_size: int = 3
    text_cache_size: int = 100
    image_cache_size: int = 20
    cache_expire_seconds: int = 300  # 5分钟缓存过期
