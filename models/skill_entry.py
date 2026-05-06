"""技能表一行（JSON / GUI / PRTS 管线键名一致）。"""

from pydantic import BaseModel


class SkillEntry(BaseModel):
    名称: str = ""
    冷却时间: str = ""
    技力消耗: str = ""
    效果: str = ""

    def is_nonempty(self) -> bool:
        return bool(self.名称 or self.冷却时间 or self.技力消耗 or self.效果)
