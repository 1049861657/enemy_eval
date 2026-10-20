"""PRTS MediaWiki API 客户端的离线契约：端点参数、超时/重试、JSON 拉取与头像 imageinfo。

全部用假 client，不发真实网络。
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx


def _run(coro):
    return asyncio.run(coro)


class TestPrtsApiClient:

    def test_default_timeout_constants(self):
        from utils.prts.api_client import DEFAULT_TIMEOUT_IMAGEINFO, DEFAULT_TIMEOUT_PARSE

        assert DEFAULT_TIMEOUT_PARSE == 22.0
        assert DEFAULT_TIMEOUT_IMAGEINFO == 12.0

    def test_build_async_client_headers_and_timeout(self):
        from utils.prts.api_client import (
            CONNECT_TIMEOUT,
            DEFAULT_TIMEOUT_PARSE,
            build_async_client,
        )

        client = build_async_client()
        try:
            assert isinstance(client, httpx.AsyncClient)
            assert "Mozilla" in client.headers["User-Agent"]
            assert client.headers["Accept-Language"].startswith("zh-CN")
            assert client.timeout.connect == CONNECT_TIMEOUT
            assert client.timeout.read == DEFAULT_TIMEOUT_PARSE
            assert client.timeout.write == DEFAULT_TIMEOUT_PARSE
            assert client.timeout.pool == CONNECT_TIMEOUT
        finally:
            _run(client.aclose())

    def test_fetch_parse_json_success(self):
        from utils.prts.api_client import _fetch_parse_json

        expected_json = {"parse": {"title": "测试敌人"}}
        response = MagicMock()
        response.json.return_value = expected_json
        response.http_version = "HTTP/2"
        client = MagicMock()
        client.get = AsyncMock(return_value=response)

        result, err = _run(_fetch_parse_json(client, "测试敌人"))
        assert result == expected_json
        assert err is None
        client.get.assert_awaited_once()
        _, call_kwargs = client.get.call_args
        assert "params" in call_kwargs
        assert call_kwargs["params"]["action"] == "parse"

    def test_fetch_parse_json_request_exception(self):
        from utils.prts.api_client import _fetch_parse_json

        client = MagicMock()
        client.get = AsyncMock(side_effect=httpx.HTTPError("网络超时"))

        result, err = _run(_fetch_parse_json(client, "测试敌人"))
        assert result is None
        assert "网络超时" in err

    def test_fetch_avatar_imageinfo_success_strips_query_string(self):
        from utils.prts.api_client import fetch_avatar_imageinfo

        raw_json = {
            "query": {
                "pages": [
                    {
                        "imageinfo": [
                            {"url": "https://example.com/avatar.png?version=1"}
                        ]
                    }
                ]
            }
        }
        response = MagicMock()
        response.json.return_value = raw_json
        response.http_version = "HTTP/1.1"
        client = MagicMock()
        client.get = AsyncMock(return_value=response)

        url, data = _run(fetch_avatar_imageinfo(client, "测试敌人"))
        assert url == "https://example.com/avatar.png"
        assert data is raw_json

    def test_fetch_avatar_imageinfo_missing_page(self):
        from utils.prts.api_client import fetch_avatar_imageinfo

        raw_json = {"query": {"pages": [{"missing": True}]}}
        response = MagicMock()
        response.json.return_value = raw_json
        response.http_version = "HTTP/2"
        client = MagicMock()
        client.get = AsyncMock(return_value=response)

        url, data = _run(fetch_avatar_imageinfo(client, "测试敌人"))
        assert url is None
        assert data is raw_json

    def test_fetch_avatar_imageinfo_no_imageinfo(self):
        from utils.prts.api_client import fetch_avatar_imageinfo

        raw_json = {"query": {"pages": [{}]}}
        response = MagicMock()
        response.json.return_value = raw_json
        response.http_version = "HTTP/2"
        client = MagicMock()
        client.get = AsyncMock(return_value=response)

        url, data = _run(fetch_avatar_imageinfo(client, "测试敌人"))
        assert url is None
        assert data is raw_json

    def test_fetch_avatar_imageinfo_exception(self):
        from utils.prts.api_client import fetch_avatar_imageinfo

        client = MagicMock()
        client.get = AsyncMock(side_effect=httpx.HTTPError("连接失败"))

        url, data = _run(fetch_avatar_imageinfo(client, "测试敌人"))
        assert url is None
        assert data == {"error": "连接失败"}

