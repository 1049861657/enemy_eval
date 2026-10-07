"""AI 评价调用层：外发字段白名单、请求、解析与错误归类。

不拼展示文案（由 GUI 层按异常子类决定），不读偏好（配置由调用方传入），不挂重试传输。
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from models import AiEvaluationResult, EnemyData

from .ai_prompt import build_messages
from .app_settings_store import AiRequestConfig
from .error_handler import (
    AiCredentialError,
    AiNetworkError,
    AiRateLimitError,
    AiServiceError,
)

logger = logging.getLogger(__name__)

# 固定读超时：长文本生成较慢，连接与写超时保持短。
AI_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)

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


def _first_json_object(text: str) -> str | None:
    """取首个括号平衡的 JSON 对象文本；对象外的前后缀文字被忽略。"""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def parse_comment(content: str) -> str:
    """从模型输出取出简评正文：剥围栏、取首个 JSON 对象、只认 comment；失败抛 AiServiceError。"""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rstrip()
        if text.endswith("```"):
            text = text[:-3]
    raw = _first_json_object(text)
    if raw is None:
        raise AiServiceError("AI 服务响应中没有可解析的 JSON 对象")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise AiServiceError("AI 服务响应的 JSON 无法解析") from error
    comment = data.get("comment") if isinstance(data, dict) else None
    if not isinstance(comment, str) or not comment.strip():
        raise AiServiceError("AI 服务响应中没有 comment 字段或内容为空")
    return comment


def _extract_content(response: httpx.Response) -> str:
    """从 chat/completions 响应体取出 assistant 正文文本。"""
    try:
        body = response.json()
    except json.JSONDecodeError as error:
        raise AiServiceError(f"AI 服务响应不是合法 JSON（HTTP {response.status_code}）") from error
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise AiServiceError(f"AI 服务响应缺少简评内容（HTTP {response.status_code}）") from error
    if not isinstance(content, str):
        raise AiServiceError("AI 服务响应的简评内容不是文本")
    return content


def _log_failure(model: str, started: float, reason: str) -> None:
    logger.warning(
        "AI 评价失败：模型=%s 耗时=%.2fs 原因=%s", model, time.perf_counter() - started, reason
    )


def evaluate(
    config: AiRequestConfig | None, baseline: dict[str, Any], current: EnemyData
) -> AiEvaluationResult:
    """一次评价调用：组包、请求、解析。

    ``config`` 为 None、HTTP 401、HTTP 429、其他错误状态码、连接失败或超时、
    响应无法解析，分别抛 AiCredentialError / AiRateLimitError / AiServiceError / AiNetworkError。
    密钥不进日志、不进异常消息。
    """
    if config is None:
        raise AiCredentialError("尚未配置 AI 服务（Base URL / 模型 / 密钥）")

    payload = {
        "model": config.model,
        "messages": build_messages(baseline, build_current_payload(current)),
    }
    url = f"{config.base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {config.api_key}"}
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=AI_TIMEOUT) as client:
            response = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as error:
        _log_failure(config.model, started, type(error).__name__)
        raise AiNetworkError(f"无法连接 AI 服务：{type(error).__name__}") from error

    status = response.status_code
    if status == 401:
        _log_failure(config.model, started, "HTTP 401")
        raise AiCredentialError("密钥无效或未授权（HTTP 401）")
    if status == 429:
        _log_failure(config.model, started, "HTTP 429")
        raise AiRateLimitError("请求过于频繁（HTTP 429）")
    if status >= 400:
        _log_failure(config.model, started, f"HTTP {status}")
        raise AiServiceError(f"AI 服务返回错误（HTTP {status}）")

    try:
        comment = parse_comment(_extract_content(response))
    except AiServiceError as error:
        _log_failure(config.model, started, type(error).__name__)
        raise
    logger.info(
        "AI 评价完成：模型=%s 耗时=%.2fs 长度=%d",
        config.model,
        time.perf_counter() - started,
        len(comment),
    )
    return AiEvaluationResult(comment=comment)
