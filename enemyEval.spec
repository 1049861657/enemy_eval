# -*- mode: python ; coding: utf-8 -*-
"""Windows 文件夹版构建：显式携带本项目的 QML 文件。"""
project_data = [
    ("resource", "resource"),
    ("gui/qml", "gui/qml"),
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
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    name="enemyEval",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    exclude_binaries=True,
)
COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    name="enemyEval",
)
