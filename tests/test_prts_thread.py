"""PRTS 拉取线程（utils/qt/prts_task.py）与主窗口并发守卫，全部离线。

PrtsFetchThread 的三条终止路径用打桩管线驱动，不发真实网络；守卫用假线程代替运行中的拉取。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from models import EnemyData
from utils.prts.field_mapping import EnemyLevel


class TestPrtsFetchThread:

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
            ratings=[
                {"name": "对策度", "score": 3},
                {"name": "创新度", "score": 3},
                {"name": "威胁度", "score": 3},
            ],
        )

    def test_signal_exists(self, qapp):
        from utils.qt.prts_task import PrtsFetchThread

        thread = PrtsFetchThread("测试敌人")
        assert hasattr(PrtsFetchThread, "fetchFinished")
        assert thread.fetchFinished is not None

    def test_run_success_emits_enemy_data(self, qapp, enemy_data, monkeypatch):
        import core.render.avatar_prefetch as prefetch
        import utils.prts.enemy_builder as builder
        import utils.prts.pipeline as pipeline
        from utils.qt.prts_task import PrtsFetchThread

        monkeypatch.setattr(
            pipeline,
            "fetch_enemy_from_prts_mediawiki_with_debug",
            AsyncMock(return_value=({"name": "测试敌人"}, {"wikitext": "页面 wikitext"})),
        )
        monkeypatch.setattr(
            pipeline,
            "parse_enemy_levels",
            Mock(return_value=[EnemyLevel(index=0, label="级别0")]),
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

        spy.assert_called_once_with(
            enemy_data,
            None,
            {
                "name": "测试敌人",
                "wikitext": "页面 wikitext",
                "levels": [{"index": 0, "label": "级别0"}],
                "level_index": 0,
            },
        )

    def test_run_error_dict_emits_mapped_message(self, qapp, monkeypatch):
        import utils.prts.pipeline as pipeline
        from utils.qt.prts_task import PrtsFetchThread

        monkeypatch.setattr(
            pipeline,
            "fetch_enemy_from_prts_mediawiki_with_debug",
            AsyncMock(return_value=({"error": "boom", "error_type": "network"}, {})),
        )
        monkeypatch.setattr(
            pipeline, "error_message_for_raw", Mock(return_value="网络错误：boom")
        )

        thread = PrtsFetchThread("测试敌人")
        spy = Mock()
        thread.fetchFinished.connect(spy)

        thread.run()

        spy.assert_called_once_with(None, "网络错误：boom", None)

    def test_run_exception_emits_message_with_exception_text(self, qapp, monkeypatch):
        import utils.prts.pipeline as pipeline
        from utils.qt.prts_task import PrtsFetchThread

        monkeypatch.setattr(
            pipeline,
            "fetch_enemy_from_prts_mediawiki_with_debug",
            AsyncMock(side_effect=ValueError("模拟异常")),
        )

        thread = PrtsFetchThread("测试敌人")
        spy = Mock()
        thread.fetchFinished.connect(spy)

        thread.run()

        args, _ = spy.call_args
        assert args[0] is None
        assert "模拟异常" in args[1]
        assert args[2] is None



class TestMainWindowPrtsFetchGuard:

    @pytest.fixture
    def main_window(self, qapp, monkeypatch):
        from gui.main_window import MainWindow

        # Avoid real rendering
        monkeypatch.setattr(MainWindow, "_generate_card", lambda self: None)

        window = MainWindow()
        yield window
        window.close()

    def test_fetch_prts_rejects_second_fetch(self, main_window):
        fake_thread = Mock()
        fake_thread.isRunning.return_value = True
        main_window.prts_fetch_thread = fake_thread

        messages = []
        main_window._bridge.messageChanged.connect(lambda message, _tone: messages.append(message))

        main_window._fetch_prts_data("新敌人")

        assert messages == ["正在获取 PRTS 数据，请稍候"]

