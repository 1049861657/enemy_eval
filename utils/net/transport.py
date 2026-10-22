"""HTTP 传输策略：超时构造、重试、代理注入与 HTTP 版本日志。

数值集中在此；调用方传自己的领域数值（PRTS 三档 read、AI 120 秒 read、更新检查 5 秒 read），
本模块不按领域分叉。超时四参数一律写全，避免 httpx 默认值随版本漂移。
重试只由 `RetryTransport` 承担：内层传输 `retries=0`，避免连接重试与外层重试相乘。
"""

from __future__ import annotations

import logging

import httpx
from httpx_retries import Retry, RetryTransport

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT = 5.0
RETRY_TOTAL = 2
RETRY_BACKOFF_FACTOR = 0.5
RETRY_STATUS_FORCELIST = (502, 503, 504)


def build_timeout(
    *,
    connect: float,
    read: float,
    write: float | None = None,
    pool: float | None = None,
) -> httpx.Timeout:
    """四参数超时；write 缺省同 read，pool 缺省同 connect。"""
    return httpx.Timeout(
        connect=connect,
        read=read,
        write=read if write is None else write,
        pool=connect if pool is None else pool,
    )


def build_retry_transport(*, async_mode: bool, proxy: str | None = None) -> RetryTransport:
    """带 HTTP/2 与代理的重试传输层；重试总次数、退避与状态码见本模块常量。

    `proxy` 为空时直连。内层不做连接重试，网络错误与 5xx 统一由 `RetryTransport` 重试。
    """
    retry = Retry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=RETRY_STATUS_FORCELIST,
    )
    if async_mode:
        inner: httpx.AsyncHTTPTransport | httpx.HTTPTransport = httpx.AsyncHTTPTransport(
            http2=True,
            retries=0,
            proxy=proxy,
        )
    else:
        inner = httpx.HTTPTransport(http2=True, retries=0, proxy=proxy)
    return RetryTransport(transport=inner, retry=retry)


def log_http_version(response: httpx.Response) -> None:
    """按 debug 级别记录响应实际使用的 HTTP 版本；域名由 logger 名体现。"""
    logger.debug("HTTP version: %s", response.http_version)
