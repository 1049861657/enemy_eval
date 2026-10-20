"""GitHub releases/latest 的条件请求。不写偏好，不带令牌。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Literal

import httpx

from utils.app.version import get_app_version

logger = logging.getLogger(__name__)

API_URL = "https://api.github.com/repos/1049861657/enemy_eval/releases/latest"
RELEASES_PAGE = "https://github.com/1049861657/enemy_eval/releases/latest"

_TIMEOUT = httpx.Timeout(connect=3, read=5, write=5, pool=5)

# SemVer 2.0.0 官方正则。预发布与构建元数据分开，构建元数据不参与比较。
_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

Outcome = Literal["update", "current", "unchanged", "none", "error"]


@dataclass(frozen=True)
class CheckResult:
    """一次 releases/latest 的结果。304 与失败不携带新的 tag / etag。"""

    outcome: Outcome
    tag: str = ""
    url: str = ""
    etag: str = ""
    retry_at: float = 0.0


def parse_semver(text: str) -> tuple[int, int, int, int] | None:
    """主、次、修订，以及正式版 1 / 预发布 0。前缀 v 去掉。无法解析时返回 None。"""
    raw = text.strip()
    if raw[:1] in ("v", "V"):
        raw = raw[1:]
    matched = _SEMVER.fullmatch(raw)
    if matched is None:
        return None
    major, minor, patch, prerelease, _build = matched.groups()
    return (int(major), int(minor), int(patch), 0 if prerelease else 1)


def is_newer(local: str, remote: str) -> bool:
    """远端正式版号高于本地时为真。任一侧无法解析则为假。"""
    left = parse_semver(local)
    right = parse_semver(remote)
    if left is None or right is None:
        return False
    return right > left


def fetch_latest(etag: str) -> CheckResult:
    """GET releases/latest。etag 非空时带 If-None-Match。异常变成 error。"""
    headers = {
        "User-Agent": f"EnemyEval/{get_app_version()}",
        "Accept": "application/vnd.github+json",
    }
    if etag:
        headers["If-None-Match"] = etag
    try:
        with httpx.Client(
            timeout=_TIMEOUT,
            headers=headers,
            follow_redirects=True,
        ) as client:
            response = client.get(API_URL)
    except Exception:
        logger.debug("版本检查失败", exc_info=True)
        return CheckResult(outcome="error")
    return _result_from_response(response)


def _result_from_response(response: httpx.Response) -> CheckResult:
    status = response.status_code
    if status == 304:
        return CheckResult(outcome="unchanged")
    if status == 404:
        return CheckResult(outcome="none")
    if status in (403, 429):
        return CheckResult(outcome="error", retry_at=_retry_at(response))
    if status != 200:
        logger.debug("版本检查状态 %s", status)
        return CheckResult(outcome="error")
    try:
        payload = response.json()
    except Exception:
        logger.debug("版本检查正文无法解析", exc_info=True)
        return CheckResult(outcome="error")
    if not isinstance(payload, dict):
        return CheckResult(outcome="error")
    tag = str(payload.get("tag_name") or "").strip()
    if not tag:
        return CheckResult(outcome="error")
    url = str(payload.get("html_url") or "").strip() or RELEASES_PAGE
    seen_etag = (response.headers.get("etag") or "").strip()
    outcome: Outcome = "update" if is_newer(get_app_version(), tag) else "current"
    return CheckResult(outcome=outcome, tag=tag, url=url, etag=seen_etag)


def _retry_at(response: httpx.Response) -> float:
    """retry-after 优先，否则 x-ratelimit-reset。都没有则为 0。"""
    now = datetime.now(timezone.utc).timestamp()
    raw_after = (response.headers.get("retry-after") or "").strip()
    if raw_after:
        try:
            return now + float(raw_after)
        except ValueError:
            parsed = parsedate_to_datetime(raw_after)
            if parsed is not None:
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.timestamp()
    raw_reset = (response.headers.get("x-ratelimit-reset") or "").strip()
    if not raw_reset:
        return 0.0
    try:
        return float(raw_reset)
    except ValueError:
        return 0.0
