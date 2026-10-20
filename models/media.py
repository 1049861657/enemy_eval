"""媒体来源判定：本地文件路径 vs 网络 URL。

位于 models：数据层零项目内依赖，任何模块按任意顺序导入都不得触发其他包初始化。
下载/缓存逻辑在 utils.net.image_fetch，它引用本模块。
"""

from __future__ import annotations

from urllib.parse import urlparse


def is_url(path: str) -> bool:
    """检查路径是否为网络URL"""
    try:
        parsed = urlparse(path)
        return parsed.scheme in ("http", "https")
    except ValueError:
        # urlparse 对畸形字符串（如包含非法端口号）通常抛 ValueError
        return False
