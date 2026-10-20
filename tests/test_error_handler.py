"""Error message categorization contract tests."""

from __future__ import annotations

from utils.errors import categorize_error_message


class TestCategorizeErrorMessage:
    def test_image_conversion_failure_returns_fixed_image_error_message(self):
        title, message = categorize_error_message(
            "图像转换失败: missing card artwork.png"
        )

        assert title == "图像处理错误"
        assert message == "卡片图像转换失败，请检查图像资源文件。"

    def test_unreadable_file_returns_fixed_file_read_error_message(self):
        title, message = categorize_error_message("无法读取配置文件: enemy.json")

        assert title == "文件读取错误"
        assert message == "无法读取必要的文件，请检查文件路径和权限。"

    def test_save_failure_preserves_original_error_detail(self):
        error_message = "保存文件失败: [Errno 13] Permission denied: 'x.json'"

        title, message = categorize_error_message(error_message)

        assert title == "保存失败"
        assert error_message in message
        assert "Permission denied" in message

    def test_load_failure_preserves_field_validation_detail(self):
        error_message = (
            "加载文件失败: 1 validation error for EnemyData\n"
            "grade\n"
            "  Value error, 等级必须是 S/A/B/C/D 中的一个"
        )

        title, message = categorize_error_message(error_message)

        assert title == "加载失败"
        assert "grade" in message
        assert "等级必须是" in message

    def test_unknown_error_returns_general_message_with_original_error(self):
        error_message = "网络请求超时: enemy service did not respond"

        title, message = categorize_error_message(error_message)

        assert title == "操作错误"
        assert error_message in message
