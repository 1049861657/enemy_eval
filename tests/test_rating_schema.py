"""全局评价标准 RatingSchema 与分数对齐工具。"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings
from pydantic import ValidationError

from models import (
    RatingSchema,
    align_rating_scores,
    default_rating_scores,
)
from utils.rating_schema_store import (
    load_rating_schema,
    save_rating_schema,
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


class TestRatingSchemaStore:
    def test_roundtrip(self, tmp_path, monkeypatch):
        settings_path = tmp_path / "settings.ini"
        monkeypatch.setattr(
            "utils.rating_schema_store._settings",
            lambda: QSettings(
                str(settings_path),
                QSettings.Format.IniFormat,
            ),
        )
        # 清空缓存
        monkeypatch.setattr("utils.rating_schema_store._cached", None)

        saved = save_rating_schema(RatingSchema(names=["甲", "乙"]))
        assert saved.names == ["甲", "乙"]

        monkeypatch.setattr("utils.rating_schema_store._cached", None)
        loaded = load_rating_schema(force_reload=True)
        assert loaded.names == ["甲", "乙"]
