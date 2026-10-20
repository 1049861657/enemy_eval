"""PRTS 管线门面（utils/prts/pipeline.py）：错误归类文案与再导出同一性。"""

from __future__ import annotations


class TestPrtsMediawikiPipelineFacade:

    def test_error_message_for_raw_mappings(self):
        from utils.prts.pipeline import error_message_for_raw

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
        import utils.prts.enemy_builder as builder
        import utils.prts.field_mapping as mapping
        import utils.prts.pipeline as facade
        import utils.prts.api_client as api

        assert facade.to_enemy_data is builder.to_enemy_data
        assert facade.strip_debug_keys is builder.strip_debug_keys
        assert facade.build_enemy_raw is mapping.build_enemy_raw
        assert facade.parse_enemy_levels is mapping.parse_enemy_levels
        assert facade.EnemyLevel is mapping.EnemyLevel
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
        from utils.prts.pipeline import fetch_enemy_data, fetch_enemy_data_raw

        assert callable(fetch_enemy_data)
        assert callable(fetch_enemy_data_raw)

