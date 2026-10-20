"""文件域：最近列表的交付格式与移除确认所需的文案参数。"""

from __future__ import annotations

import json
from pathlib import Path

from utils.app.settings import recent_files


def recent_files_json() -> str:
    """最近打开或保存过的配置；`name` 供显示，`exists` 供界面提示"文件已不在"。"""
    return json.dumps(
        [
            {"path": path, "name": Path(path).name, "exists": Path(path).is_file()}
            for path in recent_files()
        ],
        ensure_ascii=False,
    )


def recent_confirm_args(path: str) -> tuple[str, str]:
    """移除确认弹窗的两个参数：原路径与文件名。"""
    return path, Path(path).name
