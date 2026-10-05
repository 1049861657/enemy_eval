# 任务 05：便携分发与打包体积收敛

**优先级**：P2　**状态**：已完成　**依赖**：任务 01–04 全部完成后执行（打包含前四项）

**影响文件**：`pyproject.toml`、`enemyEval.spec`、`utils/app_version.py`、`gui_main.py`（冷启动打点）、新增 `scripts/build_release.py`、`uv.lock`（由 `uv lock` 生成）

## 目标

1. 依赖清单归位：打包工具不再作为运行时依赖，`uv sync` 也不再安装它；
2. 产物体积收敛：只移除确认未使用的重模块，不维护 QML 或 DLL 白名单；
3. 产出可解压即用的 zip（含校验与 SHA256），并记录体积/启动耗时前后对比。

## 现状与内部锚点

| 事实 | 锚点 |
|---|---|
| 构建入口 `gui_main.py`；`datas` 带 `resource/`、`gui/qml/`、`build_info.json`；`hiddenimports` 含四个 Qt 模块 + `numpy`/`h2`/`hpack`/`hyperframe`/`httpx_retries`/`cachetools` + 两个延迟导入的 `core` 模块；**`excludes=[]`**；`console=False`；`COLLECT name="enemyEval"` | `enemyEval.spec` |
| `pyinstaller`、`pyinstaller-hooks-contrib` 被列为**运行时依赖** | `pyproject.toml` 的 `dependencies` |
| `uv sync` 默认安装 `dev` 组。把打包工具放进 `dev` 达不到「sync 不再安装」 | `[dependency-groups].dev` 现为 pytest、pyright |
| 构建前写 `build/build_info.json`（版本 + 构建时间），收集到 `_internal/build_info.json` | `enemyEval.spec:7-33` |
| 冻结进程读构建信息走 `Path(__file__).parent.parent / "build_info.json"`。纯 Python 在 PYZ 内时，该路径对不上 `_internal/build_info.json` | `utils/app_version.py:14` |
| 界面 QML 只 `import QtQuick` / `QtQuick.Controls` / `QtQuick.Layouts`；样式为 `FluentWinUI3`，位于 `QtQuick/Controls` 之内 | `gui/qml/*.qml`、`gui_main.py:99` |

### 产物体积实测（2026-09-29，`du -sh`）

| 项 | 体积 | 说明 |
|---|---|---|
| `dist` 合计 | **466 MB** | |
| `_internal/PySide6` | 387 MB | 占 84% |
| └ `Qt6WebEngineCore.dll` | **195 MB** | 出卡片图完全用不到，单项占全产物 42% |
| └ `qml/` | 29 MB | 含 `QtWebEngine`、`Qt3D`、`QtCharts`、`QtQuick3D`、`QtMultimedia` 等未使用子树 |
| └ `opengl32sw.dll` | 20 MB | 软件 OpenGL 回退（**保留**，无显卡驱动的机器依赖它） |
| └ `translations/` | 8.4 MB | 全语言翻译 |
| `_internal/numpy.libs` | 21 MB | skia 运行时依赖（保留） |
| `_internal/skia.cp313-win_amd64.pyd` | 15 MB | 核心渲染（保留） |
| `Qt6Pdf.dll` / `Qt6ShaderTools.dll` | 4.5 / 4.2 MB | Pdf 未使用；ShaderTools 是 Qt Quick 着色器链，**保留** |

### 机制（源码级确认，2026-09-29）

| 结论 | 证据 |
|---|---|
| 基础 hook 只额外收集 ANGLE / `opengl32sw` / ICU，**不含 WebEngine** | `PyInstaller/hooks/hook-PySide6.py:28` → `PyInstaller/utils/hooks/qt/__init__.py:628 collect_extra_binaries()` |
| QML 树是**整棵**被收集的 | `PyInstaller/hooks/hook-PySide6.QtQml.py:15` → `pyside6_library_info.collect_qtqml_files()`（helper `:916`），把整棵 `PySide6/qml` 加入 binaries+datas |
| 产物内只有 `Qt6WebEngineCore.dll` / `Qt6WebEngineQuick.dll` / `Qt6WebEngineQuickDelegatesQml.dll`，**没有** `QtWebEngineCore.pyd` | `ls dist/enemyEval/_internal/PySide6` 实测 |
| 故：WebEngine DLL 是**被收集的 QML 插件的二进制依赖**连带进来的，不是某个 Python 模块被导入 | 以上三点合起来唯一解释 |
| **`Analysis.excludes` 拦不住它**（该参数是模块级排除，不删除已收集的二进制） | 见下方官方文档语义 |
| 6.21–6.22 的 `hooksconfig` 没有停止 `collect_qtqml_files` 的开关 | 本机 hook 源码与 hooks-config 文档 |

## 外部调研与出处

- **PyInstaller 维护者无法跟踪 QML import，因此收集整棵 QML 树**。`--exclude PySide6.QtQml` 只适用于不用 QML 的程序；本程序设置了 `QQuickStyle`，不能排除 `QtQml`：<https://github.com/pyinstaller/pyinstaller/issues/6447>
- **变更日志未提供「排除 QtWebEngine」的开关**：6.7.0 与 6.16.0 的相关改动只是 WebEngine 沙箱处理与 framework 结构保留：<https://pyinstaller.org/en/v6.16.0/CHANGES.html>
- **`excludes` / `--exclude-module` 只排除 Python 模块**，不删除已收集的二进制或数据：<https://pyinstaller.org/en/stable/usage.html>、<https://pyinstaller.org/en/stable/spec-files.html>。收敛在 `Analysis` 之后过滤 `analysis.binaries` / `analysis.datas`。
- **Qt 官方 `pyside6-deploy` 不维护全量白名单**。它只在 QML 源码未引用时排除六个最重的插件：`QtWebEngine`、`QtQuick3D`、`QtCharts`、`QtTest`、`QtSensors`，以及未被引用的 `QtQuick`。本程序引用了 `QtQuick`，不能排除它。文档写明只查这六个，因为体积主要在这些二进制上：<https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html>
- **同类 QML 程序的 spec**（[Mouser](https://github.com/TomBadash/Mouser/blob/master/Mouser.spec)）：`excludes` 去掉未用的 `PySide6.Qt*`，再删对应 QML 目录；`QtQuick/Controls` 整目录保留，因此 Fluent 一类样式不用点名；明确保留 `Qt6ShaderTools`。该 spec 另有一份 DLL 文件名白名单，Qt 新增依赖时会把正在用的库删掉。本任务不采用这份白名单。
- **`pyside6-deploy` 是 Nuitka 的包装**。不换工具链（见 `00-overview.md` 决策 D5）。
- **onedir 优于 onefile**：onefile 每次启动自解压到临时目录，启动更慢且更易被安全软件拦截。`upx=False` 保持不变。

## 设计

### 1. 依赖清单归位

`pyproject.toml`：把 `pyinstaller`、`pyinstaller-hooks-contrib` 从 `dependencies` 移到新建的 `[dependency-groups].build`。不把 `build` 写入 `[tool.uv] default-groups`（缺省时只有 `dev` 会随 `uv sync` 安装）。随后 `uv lock` + `uv sync`（**禁止手改 `uv.lock`**）。构建命令：

```
uv run --group build -- pyinstaller --noconfirm --clean enemyEval.spec
```

### 2. spec 层收敛

`Analysis.excludes` 写入与下表同名的 `PySide6.Qt*` 模块，减少纯 Python 模块收集。DLL 与 QML 目录仍在 `Analysis` 之后、`COLLECT` 之前按前缀删除。未出现在删除名单上的文件一律保留，包括 Qt 将来新增的库。

删除名单只含本程序 QML 未 import、且不是 Qt Quick 运行链的模块：

```
_DROP_DLL_PREFIXES = ("Qt6WebEngine", "Qt63D", "Qt6Charts", "Qt6Multimedia", "Qt6Pdf",
                      "Qt6DataVisualization", "Qt6Graphs", "Qt6Quick3D",
                      "Qt6Location", "Qt6Positioning", "Qt6TextToSpeech", "Qt6Sensors",
                      "Qt6Scxml", "Qt6RemoteObjects", "Qt6SerialPort", "Qt6Bluetooth",
                      "Qt6Nfc", "Qt6Sql", "Qt6Designer", "Qt6Help", "Qt6Test", "Qt6QuickTest",
                      "Qt6NetworkAuth", "Qt6AxContainer", "Qt6HttpServer", "Qt6WebChannel",
                      "Qt6WebSockets", "Qt6WebView", "Qt6VirtualKeyboard",
                      "Qt6SpatialAudio", "Qt6QmlLocalStorage")
_DROP_QML_DIRS = ("QtWebEngine", "Qt3D", "QtCharts", "QtQuick3D", "QtMultimedia",
                  "QtDataVisualization", "QtGraphs", "QtLocation", "QtPositioning",
                  "QtTextToSpeech", "QtSensors", "QtScxml", "QtRemoteObjects", "QtSerialPort",
                  "QtBluetooth", "QtNfc", "QtSql", "QtDesigner", "QtHelp", "QtTest",
                  "QtWebChannel", "QtWebSockets", "QtWebView", "QtVirtualKeyboard")
_DROP_QML_NESTED = ("QtQuick/VirtualKeyboard", "QtQuick/Scene2D", "QtQuick/Scene3D",
                    "QtQuick/Pdf", "QtQuick/LocalStorage")
_DROP_BASENAMES = ("qpdf.dll", "qtvirtualkeyboardplugin.dll", "qmldbg_quick3dprofiler.dll")
```

- 删除 `PySide6/qml/<名单目录>`，以及 `_DROP_QML_NESTED`。后者不在 `Controls` 里，导入表或 `qmldir` 证明它们引用了已删 DLL。`Controls`（含 `FluentWinUI3`、`Basic`、`impl`）、`Layouts`、`Templates`、`Window` 全部留下。
- `QtWebView` 的 `qmldir` 依赖 `QtWebEngine`，一并删除。
- `imageformats` 只删 `qpdf.dll`。`platforminputcontexts` 只删虚拟键盘插件。
- **不删除** `Qt6ShaderTools`、`Qt5Compat`。前者被 Qt Quick 着色器链使用；后者体积小，样式可能间接引用。
- `translations/` 只保留文件名含 `zh_CN` 的 `.qm`，其余 `.qm` 删除。

过滤之后做两道失败检查，命中则构建失败，不自动把文件加回：

1. 任一**保留**二进制的导入表出现被删 DLL 的文件名；
2. 任一**保留**的 `qmldir` 引用了 `_DROP_QML_DIRS` 中的模块。

### 3. 冻结构建信息

`utils/app_version.py` 在 `getattr(sys, "frozen", False)` 时从 `Path(sys._MEIPASS) / "build_info.json"` 读取。源码运行仍走现有的「无构建信息则读 `pyproject.toml`」路径。

### 4. 制品元信息

- 补 `icon=`（`resource/` 现有资源里选或新增 `.ico`）与 `version=`（指向 PyInstaller version 资源文件；版本值从 `pyproject.toml` 读，与 `build_info.json` 同源）。

### 5. 构建脚本 `scripts/build_release.py`

1. `uv run --group build -- pyinstaller --noconfirm --clean enemyEval.spec`；
2. 产物校验（缺一即失败）：`dist/enemyEval/enemyEval.exe`、`_internal/build_info.json`、`_internal/gui/qml`、`_internal/resource`、`opengl32sw.dll`、`Qt6ShaderTools.dll`、`qml/QtQuick/Controls`；且 `_internal/PySide6/` 下不应出现被点名剔除的 DLL/QML 目录；
3. 打 `dist/enemyEval-v{X.Y.Z}-win64.zip`；
4. 输出：zip 体积、解压后体积、SHA256。

### 6. 量化（2026-09-30）

| 项 | 值 |
|---|---|
| 优化前 `dist` | 466 MB（2026-09-29，`du -sh`） |
| 优化后解压体积 | 221022564 字节（211 MiB） |
| zip | `dist/enemyEval-v0.4.0-win64.zip`，88087675 字节（84.0 MiB） |
| SHA256 | `3d74431cc978f2f50e090526dd87989d7b629d984d2c1cfb7888553417559c39` |
| 冷启动到 QML `Status.Ready` | 1354 ms（日志 `elapsed_ms`，从进入 `main()` 起，不含之后 1.5 秒启动封面） |
| 冻结构建时间 | 日志 `built_at='2026-09-30 09:20 UTC'`，与 `build_info.json` 一致 |
| 启动后绘制 | 日志 `绘制卡片#1`，338 ms |
| 产物抽查 | 无 `Qt6WebEngineCore.dll`；有 `opengl32sw.dll`、`Qt6ShaderTools.dll`、`qml/QtQuick/Controls/FluentWinUI3`、`certifi` |

## 步骤

- [x] `pyproject.toml` 将打包工具移入 `build` 组（不加入 `default-groups`）→ `uv lock` → `uv sync` → 确认环境中没有 PyInstaller。
- [x] spec：`excludes` 写入对应 `PySide6.Qt*`；`Analysis` 之后按删除名单过滤 `binaries` / `datas`；加上导入表与 `qmldir` 两道失败检查。
- [x] 批 1–3 在同一次过滤里完成：WebEngine、名单中其余 DLL 与 QML 目录、`translations` 只留文件名含 `zh_CN` 的 `.qm`。导入表命中的插件目录已补进删除名单后构建通过。
- [x] `utils/app_version.py` 冻结时改读 `sys._MEIPASS / "build_info.json"`。
- [x] spec 补 `icon` 与 `version`。
- [x] 新增 `scripts/build_release.py`（构建 → 校验 → zip → 体积/SHA256）。
- [x] 记录前后数字。见下方量化。
- [ ] 验收冒烟仍待人工点选：打开 `data/小杂毛_config.json`、导出 PNG、关于窗口、手动检查更新。已观察到的部分见量化。`opengl32sw.dll` 以文件存在为准。

## 非目标

- 不做代码签名（未签名 exe 首次运行的系统警告属预期，不作为缺陷处理）。
- 不换打包工具链（Nuitka / `pyside6-deploy` / cx_Freeze）。
- 不维护 QML 目录白名单或 DLL 文件名白名单。
- 不裁剪 `QtQuick/Controls`，不删除 `Qt6ShaderTools`、`Qt5Compat`、`opengl32sw`、ANGLE。
- 不承诺具体瘦身数字（Qt Core/Gui/Qml/Quick 是硬成本）。
- 不精简 `numpy` / `skia`（运行时必需）。
- 不决定 `data/*_config.json` 是否随包分发（单独决策）。
- 不做自更新（任务 04 只提示）。

## 风险与回滚

| 风险 | 处置 |
|---|---|
| 删错二进制 → 启动即崩 | 删除名单排除 ShaderTools 与 `QtQuick/Controls`；导入表命中被删 DLL 时构建失败 |
| 样式或 QML 插件在运行时才加载，导入表看不出来 | 保留的 `qmldir` 若引用删除名单中的模块，构建失败；`QtQuick/Controls` 整目录保留 |
| 无显卡驱动机器启动失败 | 保留 `opengl32sw.dll` 与 ANGLE；不把它们放进删除名单 |
| 图像格式或 TLS 插件缺失 | 不按插件目录做保留名单；只删删除名单点名的 DLL 与 QML 目录，`plugins/imageformats`、`plugins/tls` 留下 |
| 有显卡的冒烟发现不了软件 OpenGL 问题 | 验收检查 `opengl32sw.dll` 仍在产物中 |
| 反复构建耗时 | 每次只动一批；构建产物不入库（`dist/`、`build/` 已被忽略） |
| 回滚 | 删除 spec 中的过滤段即回到当前收集行为；依赖组回滚为一次 `uv lock` |

## 验收

1. 干净 Windows（无 Python、无 uv）解压 zip → 双击 `enemyEval.exe` → 启动且为 Fluent 样式、打开一份配置、导出 PNG、关于窗口显示版本与构建时间、手动检查更新能发出 HTTPS。
2. `dist` 内不再包含 `Qt6WebEngineCore.dll` 与删除名单中的模块；仍包含 `opengl32sw.dll`、`Qt6ShaderTools.dll`、`qml/QtQuick/Controls`。zip 体积与解压后体积有记录。
3. `uv sync` 后环境中没有 PyInstaller。`uv run --group build -- pyinstaller` 可以构建。
4. 启动耗时与优化前的实测值并列记录。
