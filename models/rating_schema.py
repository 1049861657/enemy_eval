"""评价维度名称规则，以及编辑草稿到分数的投影。颜色由渲染色板按索引取，不进配置。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

DEFAULT_RATING_NAMES: list[str] = ["对策度", "创新度", "威胁度"]
MAX_RATING_DIMENSIONS = 5
DEFAULT_RATING_SCORE = 3


def clean_rating_name(name: str) -> str:
    """去掉首尾空白。空名、超过 8 个字符则拒绝。"""
    text = (name or "").strip()
    if not text:
        raise ValueError("评价维度名称不能为空")
    if len(text) > 8:
        raise ValueError("评价维度名称最多 8 个字符")
    return text


class RatingEntry(BaseModel):
    """一条评价。列表顺序即卡片从上到下的顺序。"""

    name: str
    score: int

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return clean_rating_name(value)

    @field_validator("score")
    @classmethod
    def validate_score(cls, value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("评分必须是整数")
        if value < 1 or value > 5:
            raise ValueError("评分必须在 1-5 之间")
        return value


class RatingSchema(BaseModel):
    """0~5 个维度名称。全局设置里的这一份是新建卡片的模板。"""

    names: list[str] = Field(
        default_factory=lambda: list(DEFAULT_RATING_NAMES),
        max_length=MAX_RATING_DIMENSIONS,
        description="评价维度显示名，顺序即卡片从上到下顺序",
    )

    @field_validator("names")
    @classmethod
    def validate_names(cls, v: list[str]) -> list[str]:
        if len(v) > MAX_RATING_DIMENSIONS:
            raise ValueError(f"评价维度最多 {MAX_RATING_DIMENSIONS} 个")
        return [clean_rating_name(name) for name in v]


def scores_for_rating_draft(scores: list[int], draft_ids: list[str]) -> list[int]:
    """按草稿行 id 取分。id 为编辑开始时的下标字符串则沿用该分，新行取默认分。"""
    kept: list[int] = []
    for item_id in draft_ids:
        if item_id.isdigit():
            index = int(item_id)
            if 0 <= index < len(scores):
                kept.append(scores[index])
                continue
        kept.append(DEFAULT_RATING_SCORE)
    return kept


def default_ratings(names: list[str]) -> list[RatingEntry]:
    """每个名称一条，分数均为默认分。"""
    return [RatingEntry(name=name, score=DEFAULT_RATING_SCORE) for name in names]
