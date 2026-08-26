"""全局评价标准 RatingSchema 与分数对齐工具。"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from models import (
    RatingSchema,
    align_rating_scores,
    default_rating_scores,
)
from utils.app_settings_store import (
    is_rating_radar,
    load_rating_schema,
    save_rating_schema,
    set_rating_radar,
)


class TestRatingSchema:
    def test_default_has_three_names(self):
        schema = RatingSchema()
        assert schema.names == ["对策度", "创新度", "威胁度"]

    def test_accepts_empty_names(self):
        schema = RatingSchema(names=[])
        assert schema.names == []

    def test_rejects_more_than_five(self):
        with pytest.raises(ValidationError):
            RatingSchema(names=["a", "b", "c", "d", "e", "f"])

    def test_rejects_blank_name(self):
        with pytest.raises(ValidationError):
            RatingSchema(names=["对策度", "  "])

    def test_strips_name_whitespace(self):
        schema = RatingSchema(names=[" 对策度 "])
        assert schema.names == ["对策度"]


class TestAlignRatingScores:
    def test_pads_with_default(self):
        assert align_rating_scores([1], 3) == [1, 3, 3]

    def test_truncates(self):
        assert align_rating_scores([1, 2, 3, 4], 2) == [1, 2]

    def test_empty_dimensions(self):
        assert align_rating_scores([1, 2], 0) == []

    def test_default_scores_helper(self):
        assert default_rating_scores(2) == [3, 3]


class TestAppSettingsStore:
    def test_roundtrip(self, app_settings_file: Path):
        saved = save_rating_schema(RatingSchema(names=["甲", "乙"]))
        assert saved.names == ["甲", "乙"]
        set_rating_radar(True)

        loaded = load_rating_schema(force_reload=True)
        assert loaded.names == ["甲", "乙"]
        assert is_rating_radar(force_reload=True) is True
        assert app_settings_file.is_file()

    def test_missing_file_uses_defaults(self, app_settings_file: Path):
        assert not app_settings_file.exists()
        schema = load_rating_schema()
        assert schema.names == ["对策度", "创新度", "威胁度"]
        assert is_rating_radar() is False

    def test_corrupt_file_uses_defaults(self, app_settings_file: Path):
        app_settings_file.write_text("{not valid json", encoding="utf-8")
        schema = load_rating_schema(force_reload=True)
        assert schema.names == ["对策度", "创新度", "威胁度"]
        assert is_rating_radar(force_reload=True) is False
