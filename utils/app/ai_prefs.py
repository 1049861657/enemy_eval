"""AI 评价配置：Base URL / 模型名 / 密钥 / 人设。

契约：Base URL 落盘前一律经 normalize_ai_base_url；形状不合法抛 ValueError，写盘失败抛
FileOperationError（不静默降级，界面据此区分成败）；密钥按明文写入偏好。写盘只经
utils/app/settings.py::update_settings。
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

from .net_prefs import proxy_mode
from .settings import load_app_settings, update_settings


@dataclass(frozen=True)
class AiRequestConfig:
    """AI 评价调用配置；Base URL / 模型 / 密钥三项均非空才有效。

    `trust_env` 表示是否跟随系统代理；False 时显式直连，但保留环境 CA。
    """

    base_url: str
    model: str
    api_key: str
    trust_env: bool


def ai_request_config() -> AiRequestConfig | None:
    """AI 调用配置；三项去空白后缺任一即视为未配置。"""
    settings = load_app_settings()
    config = AiRequestConfig(
        base_url=settings.ai_base_url.strip(),
        model=settings.ai_model.strip(),
        api_key=settings.ai_api_key.strip(),
        trust_env=proxy_mode() == "system",
    )
    if not all((config.base_url, config.model, config.api_key)):
        return None
    return config


# 用户可能把完整操作地址粘进来；这些尾段属于调用层拼接的部分。
_CHAT_PATH_SUFFIXES = ("/chat/completions", "/completions")


def normalize_ai_base_url(base_url: str) -> str:
    """把用户填的地址规范成「到版本段为止」的 Base URL。

    接受根地址、根地址 + 版本段、乃至完整的 chat 地址；path 为空时补默认版本段 `/v1`，
    path 命中操作端点时去掉该段，末尾斜杠一律去掉。自定义版本段（如 `/v1beta/openai`）
    与查询串以外的前缀原样保留——查询串与片段不属于 Base URL，丢弃。
    """
    text = base_url.strip()
    if not text:
        raise ValueError("Base URL 不能为空")
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Base URL 需要形如 https://主机，例如 https://api.deepseek.com")
    path = parsed.path.rstrip("/")
    for suffix in _CHAT_PATH_SUFFIXES:
        if path.endswith(suffix):
            path = path[: -len(suffix)].rstrip("/")
            break
    if not path:
        path = "/v1"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def ai_base_url_preview(base_url: str) -> str:
    """该地址最终会请求到的完整 URL；无法解析时返回空串（供界面显示）。"""
    try:
        normalized = normalize_ai_base_url(base_url)
    except ValueError:
        return ""
    return f"{normalized}/chat/completions"


def save_ai_settings(base_url: str, model: str, api_key: str) -> None:
    """写入 AI 调用配置（Base URL 规范化后落盘），其余偏好字段保留。

    形状不合法抛 ValueError，写盘失败抛 FileOperationError。
    """
    valid_base_url = normalize_ai_base_url(base_url)
    valid_model = model.strip()
    if not valid_model:
        raise ValueError("模型名不能为空")
    update_settings(
        ai_base_url=valid_base_url,
        ai_model=valid_model,
        ai_api_key=api_key.strip(),
    )


def save_ai_persona(persona: str) -> None:
    """写入自定义人设；空串表示沿用内置默认。写盘失败抛 FileOperationError。"""
    update_settings(ai_persona=persona.strip())
