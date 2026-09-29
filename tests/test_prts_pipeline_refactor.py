"""PRTS 数据管线契约测试。

Covers:
1. utils/prts_api_client.py — client/retry/timeout + JSON fetch + avatar imageinfo.
2. utils/prts_mediawiki_pipeline.py — facade re-exports and error message mapping.
3. utils/thread_manager.py::PrtsFetchThread — run() success/error/exception paths.
4. core/optimization.py / core.render.avatar_prefetch — shared global image cache lock.
5. gui/main_window.py — QML 发起的 PRTS 请求并发保护。

No real network calls, no real Skia network-image decodes, no hangs.
"""

from __future__ import annotations

import asyncio
import threading
from unittest.mock import AsyncMock, MagicMock, Mock

import httpx
import pytest

from models import EnemyData


def _run(coro):
    return asyncio.run(coro)


class TestPrtsApiClient:
    """utils/prts_api_client.py"""

    def test_default_timeout_constants(self):
        from utils.prts_api_client import DEFAULT_TIMEOUT_IMAGEINFO, DEFAULT_TIMEOUT_PARSE

        assert DEFAULT_TIMEOUT_PARSE == 22.0
        assert DEFAULT_TIMEOUT_IMAGEINFO == 12.0

    def test_build_async_client_headers_and_timeout(self):
        from utils.prts_api_client import (
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
        from utils.prts_api_client import _fetch_parse_json

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
        from utils.prts_api_client import _fetch_parse_json

        client = MagicMock()
        client.get = AsyncMock(side_effect=httpx.HTTPError("网络超时"))

        result, err = _run(_fetch_parse_json(client, "测试敌人"))
        assert result is None
        assert "网络超时" in err

    def test_fetch_avatar_imageinfo_success_strips_query_string(self):
        from utils.prts_api_client import fetch_avatar_imageinfo

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
        from utils.prts_api_client import fetch_avatar_imageinfo

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
        from utils.prts_api_client import fetch_avatar_imageinfo

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
        from utils.prts_api_client import fetch_avatar_imageinfo

        client = MagicMock()
        client.get = AsyncMock(side_effect=httpx.HTTPError("连接失败"))

        url, data = _run(fetch_avatar_imageinfo(client, "测试敌人"))
        assert url is None
        assert data == {"error": "连接失败"}


class TestPrtsMediawikiPipelineFacade:
    """utils/prts_mediawiki_pipeline.py — facade error mapping and re-export identity."""

    def test_error_message_for_raw_mappings(self):
        from utils.prts_mediawiki_pipeline import error_message_for_raw

        missing = {"error_type": "missing_page", "error": "无"}
        assert "未找到敌人" in error_message_for_raw(missing, "测试敌人")

        parse_empty = {"error_type": "parse_empty", "error": "无属性"}
        assert "无法解析出敌人属性" in error_message_for_raw(parse_empty, "测试")

        network = {"error_type": "network", "error": "超时"}
        assert "网络错误" in error_message_for_raw(network, "测试")

        other = {"error_type": "unknown", "error": "出错了"}
        msg = error_message_for_raw(other, "测试")
        assert "获取PRTS数据失败" in msg
        assert "出错了" in msg

    def test_facade_re_exports_source_objects(self):
        import utils.prts_enemy_builder as builder
        import utils.prts_field_mapping as mapping
        import utils.prts_mediawiki_pipeline as facade
        import utils.prts_api_client as api

        assert facade.to_enemy_data is builder.to_enemy_data
        assert facade.strip_debug_keys is builder.strip_debug_keys
        assert facade.merge_wikitext_enemy is mapping.merge_wikitext_enemy
        assert facade.LEVEL_TEMPLATE is mapping.LEVEL_TEMPLATE
        assert facade.COMMON_TEMPLATE is mapping.COMMON_TEMPLATE
        assert facade.LEVEL_KEY_MAP is mapping.LEVEL_KEY_MAP
        assert facade.COMMON_KEY_MAP is mapping.COMMON_KEY_MAP
        assert facade.ABNORMAL_MAP is mapping.ABNORMAL_MAP
        assert facade.build_async_client is api.build_async_client
        assert facade.build_client is api.build_client
        assert facade._fetch_parse_json is api._fetch_parse_json
        assert facade.fetch_avatar_imageinfo is api.fetch_avatar_imageinfo
        assert facade.PRTS_MEDIAWIKI_API is api.PRTS_MEDIAWIKI_API

    def test_fetch_enemy_data_and_raw_importable(self):
        from utils.prts_mediawiki_pipeline import fetch_enemy_data, fetch_enemy_data_raw

        assert callable(fetch_enemy_data)
        assert callable(fetch_enemy_data_raw)


class TestPrtsFetchThread:
    """utils/thread_manager.py::PrtsFetchThread — run() without real network."""

    @pytest.fixture
    def enemy_data(self):
        return EnemyData(
            name="测试敌人",
            grade="B",
            attack_type="近战",
            damage_type="物理",
            action_type="地面",
            hp_recovery_speed=0.0,
            position="普通",
            category="其他",
            max_hp=1000,
            attack=100,
            defense=50,
            magic_resistance=10,
            attack_range_radius=0.0,
            weight_level=1,
            move_speed=1.0,
            attack_interval=2.0,
            damage_resistance=0,
            element_resistance=0,
            base_taunt_level=0,
            target_value=1,
            brief_description="来自PRTS的测试敌人数据",
            brief_comment="待评价",
            rating_scores=[3, 3, 3],
        )

    def test_signal_exists(self, qapp):
        from utils.thread_manager import PrtsFetchThread

        thread = PrtsFetchThread("测试敌人")
        # Signal must be attached to the class and callable for connect
        assert hasattr(PrtsFetchThread, "fetchFinished")
        assert thread.fetchFinished is not None

    def test_run_success_emits_enemy_data(self, qapp, enemy_data, monkeypatch):
        import core.render.avatar_prefetch as prefetch
        import utils.prts_enemy_builder as builder
        import utils.prts_mediawiki_pipeline as pipeline
        from utils.thread_manager import PrtsFetchThread

        monkeypatch.setattr(
            pipeline,
            "fetch_enemy_from_prts_mediawiki",
            AsyncMock(return_value={"name": "测试敌人"}),
        )
        monkeypatch.setattr(
            builder, "strip_debug_keys", Mock(return_value={"name": "测试敌人"})
        )
        monkeypatch.setattr(builder, "to_enemy_data", Mock(return_value=enemy_data))
        monkeypatch.setattr(prefetch, "preload_network_avatar_image", AsyncMock())

        thread = PrtsFetchThread("测试敌人")
        spy = Mock()
        thread.fetchFinished.connect(spy)

        thread.run()

        spy.assert_called_once_with(enemy_data, None)

    def test_run_error_dict_emits_mapped_message(self, qapp, monkeypatch):
        import utils.prts_mediawiki_pipeline as pipeline
        from utils.thread_manager import PrtsFetchThread

        monkeypatch.setattr(
            pipeline,
            "fetch_enemy_from_prts_mediawiki",
            AsyncMock(return_value={"error": "boom", "error_type": "network"}),
        )
        monkeypatch.setattr(
            pipeline, "error_message_for_raw", Mock(return_value="网络错误：boom")
        )

        thread = PrtsFetchThread("测试敌人")
        spy = Mock()
        thread.fetchFinished.connect(spy)

        thread.run()

        spy.assert_called_once_with(None, "网络错误：boom")

    def test_run_exception_emits_message_with_exception_text(self, qapp, monkeypatch):
        import utils.prts_mediawiki_pipeline as pipeline
        from utils.thread_manager import PrtsFetchThread

        monkeypatch.setattr(
            pipeline,
            "fetch_enemy_from_prts_mediawiki",
            AsyncMock(side_effect=ValueError("模拟异常")),
        )

        thread = PrtsFetchThread("测试敌人")
        spy = Mock()
        thread.fetchFinished.connect(spy)

        thread.run()

        args, _ = spy.call_args
        assert args[0] is None
        assert "模拟异常" in args[1]


class TestGlobalImageCacheLock:
    """core/optimization.py — shared lock between optimization and avatar_prefetch."""

    def test_global_image_cache_lock_exists(self):
        from core import optimization as opt

        assert hasattr(opt, "_GLOBAL_IMAGE_CACHE_LOCK")
        assert isinstance(opt._GLOBAL_IMAGE_CACHE_LOCK, threading.Lock)

    def test_avatar_prefetch_imports_same_lock(self):
        import core.optimization as opt
        import core.render.avatar_prefetch as prefetch

        assert prefetch._GLOBAL_IMAGE_CACHE_LOCK is opt._GLOBAL_IMAGE_CACHE_LOCK


class TestMainWindowPrtsFetchGuard:
    """gui/main_window.py — QML 发起的 PRTS 请求必须防止并发拉取。"""

    @pytest.fixture
    def main_window(self, qapp, monkeypatch):
        from gui.main_window import MainWindow

        # Avoid real rendering
        monkeypatch.setattr(MainWindow, "_generate_card", lambda self: None)

        window = MainWindow()
        yield window
        window.close()

    def test_fetch_prts_rejects_second_fetch(self, main_window):
        # Simulate a running fetch thread
        fake_thread = Mock()
        fake_thread.isRunning.return_value = True
        main_window.prts_fetch_thread = fake_thread

        messages = []
        main_window._bridge.messageChanged.connect(messages.append)

        main_window._fetch_prts_data("新敌人")

        assert messages == ["正在获取 PRTS 数据，请稍候"]
