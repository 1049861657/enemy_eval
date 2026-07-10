"""全局评价维度 schema（名称与数量）；颜色由渲染色板按索引取，不进配置。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

DEFAULT_RATING_NAMES: list[str] = ["对策度", "创新度", "威胁度"]
MAX_RATING_DIMENSIONS = 5
DEFAULT_RATING_SCORE = 3


class RatingSchema(BaseModel):
    """评价标准：0~5 个维度名称，全项目共用。"""

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
        cleaned: list[str] = []
        for name in v:
            text = (name or "").strip()
            if not text:
                raise ValueError("评价维度名称不能为空")
            if len(text) > 8:
                raise ValueError("评价维度名称最多 8 个字符")
            cleaned.append(text)
        return cleaned


def align_rating_scores(
    scores: list[int],
    dimension_count: int,
    default: int = DEFAULT_RATING_SCORE,
) -> list[int]:
    """将敌人分数列表对齐到当前维度数量（截断或补默认分）。"""
    n = max(0, min(dimension_count, MAX_RATING_DIMENSIONS))
    if len(scores) >= n:
        return list(scores[:n])
    return list(scores) + [default] * (n - len(scores))


def default_rating_scores(dimension_count: int | None = None) -> list[int]:
    n = len(DEFAULT_RATING_NAMES) if dimension_count is None else dimension_count
    return [DEFAULT_RATING_SCORE] * max(0, min(n, MAX_RATING_DIMENSIONS))
