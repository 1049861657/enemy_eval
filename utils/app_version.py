"""应用版本号：与 pyproject.toml [project].version 一致。"""

from __future__ import annotations

import importlib.metadata
from pathlib import Path


def get_app_version() -> str:
    """
    优先使用已安装分发包 `enemy-eval` 的版本；
    开发时未安装则用仓库根目录 pyproject.toml 的 [project].version。
    """
    try:
        return importlib.metadata.version("enemy-eval")
    except importlib.metadata.PackageNotFoundError:
        pass

    root = Path(__file__).resolve().parent.parent
    pyproject = root / "pyproject.toml"
    try:
        import tomllib

        with pyproject.open("rb") as f:
            data = tomllib.load(f)
        return str(data["project"]["version"])
    except Exception:
        return "0.0.0"
