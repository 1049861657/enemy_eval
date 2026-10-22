"""系统代理策略：把「跟随系统」解析成具体代理 URL。

只读环境变量与操作系统设置；不读应用偏好（偏好见 `utils/app/net_prefs.py`）。
解析顺序与 httpx 的 scheme 挂载一致：先 `https`，再 `all`；`http` 不用于 https 请求。
"""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.request import getproxies, proxy_bypass


def proxy_url_for(url: str) -> str | None:
    """该 URL 在「跟随系统」下应使用的代理；命中绕过规则或未配置时返回 None。"""
    host = urlparse(url).hostname
    if not host or proxy_bypass(host):
        return None
    proxies = getproxies()
    for scheme in ("https", "all"):
        value = proxies.get(scheme, "").strip()
        if value:
            return value if "://" in value else f"http://{value}"
    return None
