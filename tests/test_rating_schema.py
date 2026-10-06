"""评价维度名称规则与草稿分数投影。"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from models import (
    RatingSchema,
    default_ratings,
    scores_for_rating_draft,
)
from utils.app_settings_store import (
    is_rating_radar,
    load_app_settings,
    load_rating_schema,
    recent_files,
    remember_recent_file,
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


class TestScoresForRatingDraft:
    def test_keeps_score_for_original_index(self):
        assert scores_for_rating_draft([5, 1, 2], ["0", "1"]) == [5, 1]

    def test_new_row_uses_default(self):
        assert scores_for_rating_draft([5, 1], ["0", "n1"]) == [5, 3]

    def test_reorder_follows_id(self):
        assert scores_for_rating_draft([5, 1, 2], ["2", "0"]) == [2, 5]

    def test_empty_draft(self):
        assert scores_for_rating_draft([1, 2], []) == []

    def test_default_ratings_helper(self):
        ratings = default_ratings(["甲", "乙"])
        assert [item.name for item in ratings] == ["甲", "乙"]
        assert [item.score for item in ratings] == [3, 3]


class TestAppSettingsStore:
    def test_roundtrip(self, app_settings_file: Path):
        saved = save_rating_schema(RatingSchema(names=["甲", "乙"]))
        assert saved.names == ["甲", "乙"]
        set_rating_radar(True)
        config_path = str(app_settings_file.parent / "甲_config.json")
        remember_recent_file(config_path)

        loaded = load_rating_schema(force_reload=True)
        assert loaded.names == ["甲", "乙"]
        assert is_rating_radar(force_reload=True) is True
        assert recent_files() == [config_path]
        assert load_app_settings(force_reload=True).recent_files == [config_path]
        assert app_settings_file.is_file()

    def test_missing_file_uses_defaults(self, app_settings_file: Path):
        assert not app_settings_file.exists()
        schema = load_rating_schema()
        assert schema.names == ["对策度", "创新度", "威胁度"]
        assert is_rating_radar() is False
        assert recent_files() == []

    def test_corrupt_file_uses_defaults(self, app_settings_file: Path):
        app_settings_file.write_text("{not valid json", encoding="utf-8")
        schema = load_rating_schema(force_reload=True)
        assert schema.names == ["对策度", "创新度", "威胁度"]
        assert is_rating_radar(force_reload=True) is False
