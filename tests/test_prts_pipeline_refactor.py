"""PRTS pipeline refactor regression tests (todos/fix-20260706/03-prts-pipeline-refactor.md).

Covers:
1. utils/prts_api_client.py — session/retry/timeout + JSON fetch + avatar imageinfo.
2. utils/prts_mediawiki_pipeline.py — facade re-exports and error message mapping.
3. utils/thread_manager.py::PrtsFetchThread — run() success/error/exception paths.
4. core/optimization.py / core.render.avatar_prefetch — shared global image cache lock.
5. gui/main_window.py — _reference_prts double-fetch guard.

No real network calls, no real Skia network-image decodes, no hangs.
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, Mock

import pytest
import requests

from models import EnemyData


class TestPrtsApiClient:
    """utils/prts_api_client.py"""

    def test_default_timeout_constants(self):
        from utils.prts_api_client import DEFAULT_TIMEOUT_IMAGEINFO, DEFAULT_TIMEOUT_PARSE

        assert DEFAULT_TIMEOUT_PARSE == 22.0
        assert DEFAULT_TIMEOUT_IMAGEINFO == 12.0

    def test_build_session_returns_session_with_retry_adapters(self):
        from requests.adapters import HTTPAdapter

        from utils.prts_api_client import build_session

        session = build_session()
        assert isinstance(session, requests.Session)
        # Both http and https are mounted to the same adapter instance
        assert "http://" in session.adapters
        assert "https://" in session.adapters
        adapter = session.adapters["http://"]
        assert isinstance(adapter, HTTPAdapter)
        assert adapter is session.adapters["https://"]

    def test_fetch_parse_json_success(self):
        from utils.prts_api_client import _fetch_parse_json

        expected_json = {"parse": {"title": "测试敌人"}}
        response = Mock()
        response.json.return_value = expected_json
        session = Mock()
        session.get.return_value = response

        result, err = _fetch_parse_json(session, "测试敌人")
        assert result == expected_json
        assert err is None
        session.get.assert_called_once()
        _, call_kwargs = session.get.call_args
        assert "params" in call_kwargs
        assert call_kwargs["params"]["action"] == "parse"

    def test_fetch_parse_json_request_exception(self):
        from utils.prts_api_client import _fetch_parse_json

        session = Mock()
        session.get.side_effect = requests.RequestException("网络超时")

        result, err = _fetch_parse_json(session, "测试敌人")
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
        response = Mock()
        response.json.return_value = raw_json
        session = Mock()
        session.get.return_value = response

        url, data = fetch_avatar_imageinfo(session, "测试敌人")
        assert url == "https://example.com/avatar.png"
        assert data is raw_json

    def test_fetch_avatar_imageinfo_missing_page(self):
        from utils.prts_api_client import fetch_avatar_imageinfo

        raw_json = {"query": {"pages": [{"missing": True}]}}
        response = Mock()
        response.json.return_value = raw_json
        session = Mock()
        session.get.return_value = response

        url, data = fetch_avatar_imageinfo(session, "测试敌人")
        assert url is None
        assert data is raw_json

    def test_fetch_avatar_imageinfo_no_imageinfo(self):
        from utils.prts_api_client import fetch_avatar_imageinfo

        raw_json = {"query": {"pages": [{}]}}
        response = Mock()
        response.json.return_value = raw_json
        session = Mock()
        session.get.return_value = response

        url, data = fetch_avatar_imageinfo(session, "测试敌人")
        assert url is None
        assert data is raw_json

    def test_fetch_avatar_imageinfo_exception(self):
        from utils.prts_api_client import fetch_avatar_imageinfo

        session = Mock()
        session.get.side_effect = requests.RequestException("连接失败")

        url, data = fetch_avatar_imageinfo(session, "测试敌人")
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
        assert facade.build_session is api.build_session
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
            hostility_rating=3,
            innovation_rating=3,
            threat_rating=3,
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
            Mock(return_value={"name": "测试敌人"}),
        )
        monkeypatch.setattr(
            builder, "strip_debug_keys", Mock(return_value={"name": "测试敌人"})
        )
        monkeypatch.setattr(builder, "to_enemy_data", Mock(return_value=enemy_data))
        monkeypatch.setattr(prefetch, "preload_prts_avatar_image", Mock())

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
            Mock(return_value={"error": "boom", "error_type": "network"}),
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
            Mock(side_effect=ValueError("模拟异常")),
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


class TestMainWindowPrtsReferenceDoubleFetchGuard:
    """gui/main_window.py — _reference_prts must guard against concurrent fetches."""

    @pytest.fixture
    def main_window(self, qapp, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        from gui.main_window import MainWindow

        # Avoid real rendering, file dialogs, and message boxes
        monkeypatch.setattr(MainWindow, "_generate_card", lambda self: None)
        monkeypatch.setattr(QMessageBox, "information", Mock())

        window = MainWindow()
        yield window
        window.close()

    def test_reference_prts_rejects_second_fetch(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        from gui.main_window import MainWindow, PrtsReferenceDialog

        # Simulate a running fetch thread
        fake_thread = Mock()
        fake_thread.isRunning.return_value = True
        main_window.prts_fetch_thread = fake_thread

        # Spy on the dialog input so we can assert it was NOT called
        dialog_mock = Mock(return_value=("", False))
        monkeypatch.setattr(PrtsReferenceDialog, "get_enemy_name_input", dialog_mock)
        info_mock = Mock()
        monkeypatch.setattr(QMessageBox, "information", info_mock)

        main_window._reference_prts()

        dialog_mock.assert_not_called()
        info_mock.assert_called_once()
        args, _ = info_mock.call_args
        assert "请稍候" in args[1]

    def test_reference_prts_allows_first_fetch(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        from gui.main_window import MainWindow, PrtsReferenceDialog

        fake_thread = Mock()
        fake_thread.isRunning.return_value = False
        main_window.prts_fetch_thread = fake_thread

        dialog_mock = Mock(return_value=("新敌人", True))
        monkeypatch.setattr(PrtsReferenceDialog, "get_enemy_name_input", dialog_mock)
        # Stub out the actual fetch to keep this test focused on the guard
        monkeypatch.setattr(MainWindow, "_fetch_prts_data", Mock())
        info_mock = Mock()
        monkeypatch.setattr(QMessageBox, "information", info_mock)

        main_window._reference_prts()

        dialog_mock.assert_called_once()
