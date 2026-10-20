# -*- mode: python ; coding: utf-8 -*-
"""Windows 文件夹版构建：显式携带资源、QML 与 Qt Quick 模块。"""

import json
import os
import re
import struct
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pefile
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

sys.path.insert(0, str(Path(SPECPATH)))

from utils.app.identity import APP_AUTHOR, APP_NAME  # noqa: E402


project_root = Path(SPECPATH)
with (project_root / "pyproject.toml").open("rb") as pyproject_file:
    pyproject = tomllib.load(pyproject_file)
project_version = str(pyproject["project"]["version"])
project_description = str(pyproject["project"]["description"])

source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH")
if source_date_epoch is None:
    build_time = datetime.now(timezone.utc)
else:
    build_time = datetime.fromtimestamp(int(source_date_epoch), timezone.utc)

build_dir = project_root / "build"
build_dir.mkdir(parents=True, exist_ok=True)
build_info_path = build_dir / "build_info.json"
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


def _version_tuple(text: str) -> tuple[int, int, int, int]:
    parts: list[int] = []
    for piece in text.split("."):
        digits = ""
        for char in piece:
            if not char.isdigit():
                break
            digits += char
        if digits:
            parts.append(int(digits))
    while len(parts) < 4:
        parts.append(0)
    return parts[0], parts[1], parts[2], parts[3]


_file_version = _version_tuple(project_version)
_version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=_file_version, prodvers=_file_version),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "080404b0",
                    [
                        StringStruct("CompanyName", APP_AUTHOR),
                        StringStruct("FileDescription", project_description),
                        StringStruct("FileVersion", project_version),
                        StringStruct("InternalName", "enemyEval"),
                        StringStruct("OriginalFilename", "enemyEval.exe"),
                        StringStruct("ProductName", APP_NAME),
                        StringStruct("ProductVersion", project_version),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [2052, 1200])]),
    ],
)
version_info_path = build_dir / "file_version_info.txt"
version_info_path.write_text(str(_version_info), encoding="utf-8")


_ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 256)


def _scaled_icon(source: QImage, size: int) -> QImage:
    """逐步减半再收到目标边长。按预乘 alpha 缩放。"""
    image = source.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    while min(image.width(), image.height()) >= size * 2:
        image = image.scaled(
            max(image.width() // 2, 1),
            max(image.height() // 2, 1),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    image = image.scaled(
        size,
        size,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return image.convertToFormat(QImage.Format.Format_ARGB32)


def _icon_dib(image: QImage) -> bytes:
    """32 位 DIB，自下而上。AND 掩码里 alpha < 128 的像素为透明。"""
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    width = image.width()
    height = image.height()
    xor = bytearray()
    mask_row = ((width + 31) // 32) * 4
    mask = bytearray(mask_row * height)
    row_index = 0
    for y in range(height - 1, -1, -1):
        for x in range(width):
            color = image.pixel(x, y)
            alpha = (color >> 24) & 0xFF
            xor.extend(
                (
                    color & 0xFF,
                    (color >> 8) & 0xFF,
                    (color >> 16) & 0xFF,
                    alpha,
                )
            )
            if alpha < 128:
                mask[row_index * mask_row + (x // 8)] |= 0x80 >> (x % 8)
        row_index += 1
    dib = struct.pack(
        "<IIIHHIIIIII",
        40,
        width,
        height * 2,
        1,
        32,
        0,
        len(xor) + len(mask),
        0,
        0,
        0,
        0,
    )
    return dib + bytes(xor) + bytes(mask)


def _write_icon(png_path: Path, ico_path: Path) -> None:
    """把 PNG 收成多尺寸 32 位 ICO。边长 256 的目录宽高字节为 0。"""
    source = QImage(str(png_path))
    if source.isNull():
        raise SystemExit(f"无法读取图标源：{png_path}")
    payloads = [_icon_dib(_scaled_icon(source, size)) for size in _ICON_SIZES]
    header = struct.pack("<HHH", 0, 1, len(payloads))
    directory = bytearray()
    blob = bytearray()
    offset = 6 + 16 * len(payloads)
    for size, payload in zip(_ICON_SIZES, payloads, strict=True):
        dim = 0 if size >= 256 else size
        directory.extend(
            struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(payload), offset)
        )
        offset += len(payload)
        blob.extend(payload)
    ico_path.write_bytes(header + bytes(directory) + bytes(blob))


icon_path = build_dir / "enemyEval.ico"
_write_icon(project_root / "resource" / "icon.png", icon_path)

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
# httpx[http2] 惰性加载 h2；QThread.run / _pull 内延迟导入 core.render。
# skia-python 运行时依赖 numpy（C 扩展内 import），分析入口看不到。
_runtime_hiddenimports = [
    "numpy",
    "h2",
    "hpack",
    "hyperframe",
    "httpx_retries",
    "cachetools",
    "core.render.generator",
    "core.render.avatar_prefetch",
]
# 与下面的 DLL / QML 删除名单对应的 Python 模块。excludes 删不掉已收集的二进制。
_excludes = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtAxContainer",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtDesigner",
    "PySide6.QtGraphs",
    "PySide6.QtGraphsWidgets",
    "PySide6.QtHelp",
    "PySide6.QtHttpServer",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth",
    "PySide6.QtNfc",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickTest",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtWebView",
    "PySide6.QtSpatialAudio",
]

_DROP_DLL_PREFIXES = (
    "Qt6WebEngine",
    "Qt63D",
    "Qt6Charts",
    "Qt6Multimedia",
    "Qt6Pdf",
    "Qt6DataVisualization",
    "Qt6Graphs",
    "Qt6Quick3D",
    "Qt6Location",
    "Qt6Positioning",
    "Qt6TextToSpeech",
    "Qt6Sensors",
    "Qt6Scxml",
    "Qt6RemoteObjects",
    "Qt6SerialPort",
    "Qt6Bluetooth",
    "Qt6Nfc",
    "Qt6Sql",
    "Qt6Designer",
    "Qt6Help",
    "Qt6Test",
    "Qt6QuickTest",
    "Qt6NetworkAuth",
    "Qt6AxContainer",
    "Qt6HttpServer",
    "Qt6WebChannel",
    "Qt6WebSockets",
    "Qt6WebView",
    "Qt6VirtualKeyboard",
    "Qt6SpatialAudio",
    "Qt6QmlLocalStorage",
)
_DROP_QML_DIRS = frozenset(
    {
        "QtWebEngine",
        "Qt3D",
        "QtCharts",
        "QtQuick3D",
        "QtMultimedia",
        "QtDataVisualization",
        "QtGraphs",
        "QtLocation",
        "QtPositioning",
        "QtTextToSpeech",
        "QtSensors",
        "QtScxml",
        "QtRemoteObjects",
        "QtSerialPort",
        "QtBluetooth",
        "QtNfc",
        "QtSql",
        "QtDesigner",
        "QtHelp",
        "QtTest",
        "QtWebChannel",
        "QtWebSockets",
        "QtWebView",
        "QtVirtualKeyboard",
    }
)
# 这些目录在 QtQuick 里面，但不是 Controls。它们的插件引用了上面要删的 DLL。
_DROP_QML_NESTED = (
    "QtQuick/VirtualKeyboard/",
    "QtQuick/Scene2D/",
    "QtQuick/Scene3D/",
    "QtQuick/Pdf/",
    "QtQuick/LocalStorage/",
)
_DROP_BASENAMES = frozenset(
    {
        "qpdf.dll",
        "qtvirtualkeyboardplugin.dll",
        "qmldbg_quick3dprofiler.dll",
    }
)
_QMLDIR_REF = re.compile(
    r"^(?:module|depends|(?:optional\s+|default\s+)?import)\s+(\S+)",
    re.MULTILINE,
)


def _should_drop(dest: str) -> bool:
    norm = dest.replace("\\", "/")
    key = "PySide6/qml/"
    pos = norm.find(key)
    if pos >= 0:
        qml_rel = norm[pos + len(key) :]
        top, _, _tail = qml_rel.partition("/")
        if top in _DROP_QML_DIRS:
            return True
        if any(qml_rel == nested[:-1] or qml_rel.startswith(nested) for nested in _DROP_QML_NESTED):
            return True
    base = os.path.basename(norm)
    if "/translations/" in norm and base.endswith(".qm") and "zh_CN" not in base:
        return True
    if base.lower() in _DROP_BASENAMES:
        return True
    return any(base.startswith(prefix) for prefix in _DROP_DLL_PREFIXES)


def _pe_import_dlls(path: str) -> set[str]:
    try:
        pe = pefile.PE(path, fast_load=True)
    except pefile.PEFormatError:
        return set()
    try:
        pe.parse_data_directories(
            directories=[
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
            ]
        )
        names: set[str] = set()
        for attr in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT"):
            for entry in getattr(pe, attr, []):
                dll = getattr(entry, "dll", None)
                if not dll:
                    continue
                text = dll.decode("ascii", errors="ignore").replace("\\", "/")
                names.add(os.path.basename(text).lower())
        return names
    finally:
        pe.close()


def _removed_dll_names(before: list, after: list) -> set[str]:
    kept = {entry[0] for entry in after}
    names: set[str] = set()
    for entry in before:
        if entry[0] in kept:
            continue
        base = os.path.basename(entry[0]).lower()
        if base.endswith((".dll", ".pyd")):
            names.add(base)
    return names


def _assert_kept_references(binaries: list, datas: list, removed_dlls: set[str]) -> None:
    hits: list[str] = []
    for entry in binaries:
        dest, src = entry[0], entry[1]
        if not os.path.isfile(src):
            continue
        for dll in _pe_import_dlls(src):
            if dll in removed_dlls:
                hits.append(f"导入表 {dest} -> {dll}")
    for entry in datas:
        dest, src = entry[0], entry[1]
        if os.path.basename(dest) != "qmldir" or not os.path.isfile(src):
            continue
        text = Path(src).read_text(encoding="utf-8", errors="ignore")
        for module in _QMLDIR_REF.findall(text):
            for name in _DROP_QML_DIRS:
                if module == name or module.startswith(name + "."):
                    hits.append(f"qmldir {dest} -> {module}")
                    break
    if hits:
        raise SystemExit("保留文件仍引用已剔除模块，构建停止：\n" + "\n".join(hits))


analysis = Analysis(
    ["gui_main.py"],
    pathex=[],
    binaries=[],
    datas=project_data,
    hiddenimports=qt_quick_modules + _runtime_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_excludes,
    noarchive=False,
    optimize=0,
)

_binaries_before = list(analysis.binaries)
_datas_before = list(analysis.datas)
analysis.binaries = [entry for entry in analysis.binaries if not _should_drop(entry[0])]
analysis.datas = [entry for entry in analysis.datas if not _should_drop(entry[0])]
_removed_dlls = _removed_dll_names(_binaries_before, list(analysis.binaries))
_removed_dlls.update(_removed_dll_names(_datas_before, list(analysis.datas)))
print(
    f"剔除二进制 {len(_binaries_before) - len(analysis.binaries)} 个，"
    f"数据 {len(_datas_before) - len(analysis.datas)} 个"
)
_assert_kept_references(list(analysis.binaries), list(analysis.datas), _removed_dlls)

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
    icon=str(icon_path),
    version=str(version_info_path),
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
