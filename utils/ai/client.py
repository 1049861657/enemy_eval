"""AI 评价调用层：外发字段白名单、请求、正文折算与错误归类。

不拼展示文案（由 GUI 层按异常子类决定），不读偏好（配置由调用方传入），不挂重试传输。
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from models import AiEvaluationResult, EnemyData

from .prompt import build_messages
from ..app.ai_prefs import AiRequestConfig
from ..errors import (
    AiCredentialError,
    AiNetworkError,
    AiRateLimitError,
    AiServiceError,
)
from ..net.transport import build_timeout

logger = logging.getLogger(__name__)

# 固定读超时：推理类模型单次生成可能超过 60 秒，连接与写超时保持短。
AI_TIMEOUT = build_timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)

_NUMERIC_FIELDS = (
    "max_hp",
    "attack",
    "defense",
    "magic_resistance",
    "attack_range_radius",
    "weight_level",
    "move_speed",
    "attack_interval",
    "hp_recovery_speed",
    "damage_resistance",
    "element_resistance",
    "base_taunt_level",
    "target_value",
)
_ENUM_FIELDS = ("attack_type", "damage_type", "action_type", "position", "category")
_TEXT_FIELDS = ("name", "brief_description", "talents_abilities")
_SKILL_FIELDS = ("名称", "冷却时间", "技力消耗", "效果")

def build_current_payload(current: EnemyData) -> dict[str, Any]:
    """当前卡的外发字段：白名单逐字段构造，新增字段不会自动外泄。"""
    payload: dict[str, Any] = {
        key: getattr(current, key) for key in (*_NUMERIC_FIELDS, *_ENUM_FIELDS, *_TEXT_FIELDS)
    }
    payload["skills"] = [
        {key: getattr(skill, key) for key in _SKILL_FIELDS} for skill in current.skills
    ]
    return payload


def extract_comment(content: str) -> str:
    """把模型响应正文折算成简评：只去首尾空白，其余原样保留。

    产物形态由提示词契约约束（纯正文、无包装）；本层不做清洗，也不改写正文。
    """
    comment = content.strip()
    if not comment:
        raise AiServiceError("AI 服务响应为空，未产出简评")
    return comment


def _extract_content(response: httpx.Response) -> tuple[str, str]:
    """从 chat/completions 响应体取出 assistant 正文文本与结束原因（缺该键时为空白串）。"""
    try:
        body = response.json()
    except json.JSONDecodeError as error:
        raise AiServiceError(f"AI 服务响应不是合法 JSON（HTTP {response.status_code}）") from error
    try:
        choice = body["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise AiServiceError(f"AI 服务响应缺少简评内容（HTTP {response.status_code}）") from error
    if not isinstance(content, str):
        raise AiServiceError("AI 服务响应的简评内容不是文本")
    finish_reason = choice.get("finish_reason")
    return content, finish_reason if isinstance(finish_reason, str) else ""


def _status_message(status: int) -> str:
    """错误状态码文案；404 指出版本段、402 指出余额、400/422 指出模型名。"""
    if status == 404:
        return "AI 服务返回错误（HTTP 404）：该地址不存在，常见原因是 Base URL 多了或少了版本段（如 /v1）"
    if status == 402:
        return "AI 服务返回错误（HTTP 402）：账户余额或配额不足，请到供应商控制台查看"
    if status in (400, 422):
        return f"AI 服务返回错误（HTTP {status}）：请求被拒绝，请核对模型名在该服务下是否存在"
    if status == 503:
        return "AI 服务返回错误（HTTP 503）：服务繁忙，请稍后重试"
    return f"AI 服务返回错误（HTTP {status}）"


def _excerpt(text: str, limit: int = 120) -> str:
    """响应开头摘要：换行压成空格，供日志定位异常响应。"""
    flat = " ".join(text.split())
    return flat[:limit] + ("…" if len(flat) > limit else "")


def _log_failure(model: str, started: float, reason: str) -> None:
    logger.warning(
        "AI 评价失败：模型=%s 耗时=%.2fs 原因=%s", model, time.perf_counter() - started, reason
    )


def _retry_after_seconds(response: httpx.Response) -> int | None:
    """429 响应的 Retry-After 秒数；缺头、非数字或非正数时为 None。"""
    raw = response.headers.get("Retry-After", "").strip()
    if not raw.isdigit():
        return None
    seconds = int(raw)
    return seconds if seconds > 0 else None


def endpoint_url(config: AiRequestConfig) -> str:
    """chat/completions 端点；`_build_request` 与界面预览共用，避免说明与实际分家。"""
    return f"{config.base_url.rstrip('/')}/chat/completions"


def _require_config(config: AiRequestConfig | None) -> AiRequestConfig:
    """参数契约：配置为 None 时抛 AiCredentialError（GUI 侧另有门槛拦截）。"""
    if config is None:
        raise AiCredentialError("尚未配置 AI 服务（Base URL / 模型 / 密钥）")
    return config


def _build_request(
    config: AiRequestConfig,
    persona: str,
    baseline: dict[str, Any],
    current: EnemyData,
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """组包：端点 URL、认证头与请求体；请求体只带最小公共字段。"""
    payload = {
        "model": config.model,
        "messages": build_messages(persona, baseline, build_current_payload(current)),
    }
    return endpoint_url(config), {"Authorization": f"Bearer {config.api_key}"}, payload


def _network_error(error: httpx.HTTPError, model: str, started: float) -> AiNetworkError:
    """连接类失败与响应超时给不同文案：前者是网络问题，后者是模型太慢。"""
    _log_failure(model, started, type(error).__name__)
    if isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout)):
        return AiNetworkError(f"无法连接 AI 服务（{type(error).__name__}）")
    if isinstance(error, (httpx.ReadTimeout, httpx.PoolTimeout)):
        return AiNetworkError(f"AI 服务响应超时（{int(AI_TIMEOUT.read)} 秒内未返回）")
    return AiNetworkError(f"AI 请求失败（{type(error).__name__}）")


def _interpret_response(
    response: httpx.Response, model: str, started: float
) -> AiEvaluationResult:
    """状态码转异常；成功则解析简评并记一条完成日志。"""
    status = response.status_code
    if status == 401:
        _log_failure(model, started, "HTTP 401")
        raise AiCredentialError("密钥无效或未授权（HTTP 401）")
    if status == 429:
        retry_after = _retry_after_seconds(response)
        _log_failure(model, started, "HTTP 429")
        detail = f"，约 {retry_after} 秒后重试" if retry_after is not None else ""
        raise AiRateLimitError(f"请求过于频繁（HTTP 429）{detail}")
    if status >= 400:
        _log_failure(model, started, f"HTTP {status}")
        raise AiServiceError(_status_message(status))
    content, finish_reason = _extract_content(response)
    if finish_reason == "length":
        _log_failure(model, started, "finish_reason=length")
        raise AiServiceError("AI 服务响应因长度上限被截断，未产出完整简评，请重试或更换模型")
    try:
        comment = extract_comment(content)
    except AiServiceError as error:
        _log_failure(model, started, f"{type(error).__name__} 响应={_excerpt(content)}")
        raise
    logger.info(
        "AI 评价完成：模型=%s 耗时=%.2fs 长度=%d",
        model,
        time.perf_counter() - started,
        len(comment),
    )
    return AiEvaluationResult(comment=comment)


def evaluate(
    config: AiRequestConfig | None,
    persona: str,
    baseline: dict[str, Any],
    current: EnemyData,
) -> AiEvaluationResult:
    """同步评价调用：组包、请求、解析。供冒烟脚本与非 GUI 调用。

    ``persona`` 为人设正文（空则用内置默认）；``config`` 为 None、HTTP 401、HTTP 429、
    其他错误状态码、连接失败或响应超时、响应无法解析，分别抛
    AiCredentialError / AiRateLimitError / AiServiceError / AiNetworkError。
    密钥不进日志、不进异常消息。
    """
    ready = _require_config(config)
    url, headers, payload = _build_request(ready, persona, baseline, current)
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=AI_TIMEOUT) as client:
            response = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as error:
        raise _network_error(error, ready.model, started) from error
    return _interpret_response(response, ready.model, started)


async def aevaluate(
    config: AiRequestConfig | None,
    persona: str,
    baseline: dict[str, Any],
    current: EnemyData,
) -> AiEvaluationResult:
    """异步评价调用：传输层换 AsyncClient，使在飞请求可被 `task.cancel()` 取消。

    组包、解析与异常映射与 ``evaluate`` 同源，两者行为一致。
    """
    ready = _require_config(config)
    url, headers, payload = _build_request(ready, persona, baseline, current)
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as error:
        raise _network_error(error, ready.model, started) from error
    return _interpret_response(response, ready.model, started)
