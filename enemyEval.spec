# -*- mode: python ; coding: utf-8 -*-
"""Windows 文件夹版构建：显式携带资源、QML 与 Qt Quick 模块。"""

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
