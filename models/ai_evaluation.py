"""AI 评价结果模型。"""

from pydantic import BaseModel, Field, field_validator


class AiEvaluationResult(BaseModel):
    """一次 AI 评价的产出：简评正文。长度上限是提示词约束，本层不裁剪。"""

    comment: str = Field(..., description="简评正文；原样保留")

    @field_validator("comment")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        """拒绝空串与纯空白。"""
        if not value.strip():
            raise ValueError("简评不能为空")
        return value
