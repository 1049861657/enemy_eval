"""应用版本与构建信息。"""

from __future__ import annotations

import json
import tomllib
from datetime import datetime
from importlib import metadata
from pathlib import Path


def _load_build_info() -> dict[str, object]:
    """读取 PyInstaller 在打包阶段写入的制品元数据。"""
    path = Path(__file__).resolve().parent.parent / "build_info.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get_app_version() -> str:
    """
    优先使用已安装分发包 `enemy-eval` 的版本；
    冻结制品使用打包元数据，源码开发时读取 pyproject.toml。
    """
    try:
        return metadata.version("enemy-eval")
    except metadata.PackageNotFoundError:
        pass

    build_version = _load_build_info().get("version")
    if isinstance(build_version, str):
        return build_version

    root = Path(__file__).resolve().parent.parent
    pyproject = root / "pyproject.toml"
    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
        return str(data["project"]["version"])
    except Exception:
        return "0.0.0"


def get_app_build_time() -> str | None:
    """返回适合 About 展示的 UTC 构建时间；源码运行时返回 None。"""
    value = _load_build_info().get("built_at")
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return timestamp.strftime("%Y-%m-%d %H:%M UTC")
