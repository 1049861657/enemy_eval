# -*- mode: python ; coding: utf-8 -*-
"""Windows 文件夹版构建：显式携带资源、QML 与 Qt Quick 模块。"""

import json
import os
import tomllib
from datetime import datetime, timezone
from pathlib import Path


project_root = Path(SPECPATH)
with (project_root / "pyproject.toml").open("rb") as pyproject_file:
    project_version = str(tomllib.load(pyproject_file)["project"]["version"])

source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH")
if source_date_epoch is None:
    build_time = datetime.now(timezone.utc)
else:
    build_time = datetime.fromtimestamp(int(source_date_epoch), timezone.utc)

build_info_path = project_root / "build" / "build_info.json"
build_info_path.parent.mkdir(parents=True, exist_ok=True)
build_info_path.write_text(
    json.dumps(
        {
            "version": project_version,
            "built_at": build_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

project_data = [
    ("resource", "resource"),
    ("gui/qml", "gui/qml"),
    (str(build_info_path), "."),
]
qt_quick_modules = [
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
]

analysis = Analysis(
    ["gui_main.py"],
    pathex=[],
    binaries=[],
    datas=project_data,
    hiddenimports=qt_quick_modules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="enemyEval",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="enemyEval",
)
