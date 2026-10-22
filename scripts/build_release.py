#!/usr/bin/env python3
"""
打 Windows 便携包：构建、校验、zip、SHA256。

用法（项目根目录）:
  uv run python scripts/build_release.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# 与 enemy_eval.spec 的删除名单一致。
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
_DROP_QML_NESTED = (
    "QtQuick/VirtualKeyboard",
    "QtQuick/Scene2D",
    "QtQuick/Scene3D",
    "QtQuick/Pdf",
    "QtQuick/LocalStorage",
)
_DROP_BASENAMES = frozenset(
    {
        "qpdf.dll",
        "qtvirtualkeyboardplugin.dll",
        "qmldbg_quick3dprofiler.dll",
    }
)


def _project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as pyproject_file:
        return str(tomllib.load(pyproject_file)["project"]["version"])


def _dir_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _find_named(root: Path, name: str) -> bool:
    return any(item.name == name for item in root.rglob(name) if item.is_file())


def _validate(dist: Path) -> None:
    internal = dist / "_internal"
    required = [
        dist / "enemyEval.exe",
        internal / "build_info.json",
        internal / "gui" / "qml",
        internal / "resource",
        internal / "resource" / "fonts" / "HarmonyOS_Sans_SC_Regular.ttf",
        internal / "resource" / "fonts" / "LICENSE.txt",
        internal / "PySide6" / "qml" / "QtQuick" / "Controls",
    ]
    missing = [str(path.relative_to(dist)) for path in required if not path.exists()]
    if not _find_named(internal, "opengl32sw.dll"):
        missing.append("opengl32sw.dll")
    if not _find_named(internal, "Qt6ShaderTools.dll"):
        missing.append("Qt6ShaderTools.dll")
    if missing:
        raise SystemExit("产物缺少：\n" + "\n".join(missing))

    pyside = internal / "PySide6"
    forbidden: list[str] = []
    for item in pyside.rglob("*"):
        if item.name.lower() in _DROP_BASENAMES or any(
            item.name.startswith(prefix) for prefix in _DROP_DLL_PREFIXES
        ):
            forbidden.append(str(item.relative_to(dist)))
    qml_root = pyside / "qml"
    if qml_root.is_dir():
        for name in _DROP_QML_DIRS:
            dropped = qml_root / name
            if dropped.exists():
                forbidden.append(str(dropped.relative_to(dist)))
        for nested in _DROP_QML_NESTED:
            dropped = qml_root.joinpath(*nested.split("/"))
            if dropped.exists():
                forbidden.append(str(dropped.relative_to(dist)))
    translations = pyside / "translations"
    if translations.is_dir():
        for item in translations.glob("*.qm"):
            if "zh_CN" not in item.name:
                forbidden.append(str(item.relative_to(dist)))
    if forbidden:
        raise SystemExit("产物仍含应剔除文件：\n" + "\n".join(forbidden))


def _zip(dist: Path, archive_path: Path) -> None:
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for item in dist.rglob("*"):
            if item.is_file():
                archive.write(item, item.relative_to(dist.parent).as_posix())


def main() -> int:
    version = _project_version()
    subprocess.run(
        [
            "uv",
            "run",
            "--group",
            "build",
            "--",
            "pyinstaller",
            "--noconfirm",
            "--clean",
            "enemy_eval.spec",
        ],
        cwd=ROOT,
        check=True,
    )
    dist = ROOT / "dist" / "enemyEval"
    _validate(dist)
    archive_path = ROOT / "dist" / f"enemyEval-v{version}-win64.zip"
    _zip(dist, archive_path)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    unpacked = _dir_size(dist)
    packed = archive_path.stat().st_size
    print(f"解压后体积 {unpacked} 字节")
    print(f"zip 体积 {packed} 字节")
    print(f"SHA256 {digest}")
    print(archive_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
