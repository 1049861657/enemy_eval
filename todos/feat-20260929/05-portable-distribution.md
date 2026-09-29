# 任务 05：便携分发与打包体积收敛

**优先级**：P2　**状态**：未开始　**依赖**：任务 01–04 全部完成后执行（打包含前四项）

**影响文件**：`pyproject.toml`、`enemyEval.spec`、新增 `scripts/build_release.py`、`uv.lock`（由 `uv lock` 生成）

## 目标

1. 依赖清单归位：打包工具不再作为运行时依赖；
2. 产物体积收敛：移除产物中未使用的 Qt 二进制与 QML 子树；
3. 产出可解压即用的 zip（含校验与 SHA256），并记录体积/启动耗时前后对比。

## 现状与内部锚点

| 事实 | 锚点 |
|---|---|
| 构建入口 `gui_main.py`；`datas` 带 `resource/`、`gui/qml/`、`build_info.json`；`hiddenimports` 含四个 Qt 模块 + `numpy`/`h2`/`hpack`/`hyperframe`/`httpx_retries`/`cachetools` + 两个延迟导入的 `core` 模块；**`excludes=[]`**；`console=False`；`COLLECT name="enemyEval"` | `enemyEval.spec` |
| `pyinstaller`、`pyinstaller-hooks-contrib` 被列为**运行时依赖** | `pyproject.toml` 的 `dependencies` |
| 构建前写 `build/build_info.json`（版本 + 构建时间） | `enemyEval.spec:7-33`、`utils/app_version.py:12` |
| 入口只 import QtQuick 系（QML 侧 `import QtQuick.Controls`），并设置 `QQuickStyle` | `gui_main.py:99` |

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
| `Qt6Pdf.dll` / `Qt6ShaderTools.dll` | 4.5 / 4.2 MB | 未使用 |

### 机制（源码级确认，2026-09-29）

| 结论 | 证据 |
|---|---|
| 基础 hook 只额外收集 ANGLE / `opengl32sw` / ICU，**不含 WebEngine** | `PyInstaller/hooks/hook-PySide6.py:28` → `PyInstaller/utils/hooks/qt/__init__.py:628 collect_extra_binaries()` |
| QML 树是**整棵**被收集的 | `PyInstaller/hooks/hook-PySide6.QtQml.py:15` → `pyside6_library_info.collect_qtqml_files()`（helper `:916`），把整棵 `PySide6/qml` 加入 binaries+datas |
| 产物内只有 `Qt6WebEngineCore.dll` / `Qt6WebEngineQuick.dll` / `Qt6WebEngineQuickDelegatesQml.dll`，**没有** `QtWebEngineCore.pyd` | `ls dist/enemyEval/_internal/PySide6` 实测 |
| 故：WebEngine DLL 是**被收集的 QML 插件的二进制依赖**连带进来的，不是某个 Python 模块被导入 | 以上三点合起来唯一解释 |
| **`Analysis.excludes` 拦不住它**（该参数是模块级排除，不删除已收集的二进制） | 见下方官方文档语义 |

## 外部调研与出处

- **PyInstaller 的 Qt hook 会带走整个 Qt 包**（社区 issue：Linux 上 Hello World 也能 >600 MB，含 `libQt6WebEngineCore.so.6` 约 175 MB）：<https://github.com/pyinstaller/pyinstaller/issues/6447>
- **变更日志未提供"排除 QtWebEngine"的开关**：6.7.0 与 6.16.0 的相关改动只是 WebEngine 沙箱处理与 framework 结构保留，没有排除选项：<https://pyinstaller.org/en/v6.16.0/CHANGES.html>
- **`excludes` / `--exclude-module` 的语义是"排除 Python 模块"**，不是"删除已收集的二进制/数据"：<https://pyinstaller.org/en/stable/usage.html>、<https://pyinstaller.org/en/stable/spec-files.html>（`Analysis` 参数说明）→ 本任务的收敛必须在 **spec 层过滤** `analysis.binaries` / `analysis.datas`。
- **`pyside6-deploy` 是 Nuitka 的包装**，Qt 官方部署文档承认 Nuitka 路线同样可能拉入未使用的 Qt 大模块；体积实测对比（库依赖多时 PyInstaller 的 onedir 更小：242 MB vs 252 MB 一例；Nuitka 启动更快但构建更慢、单文件更大）：<https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html>、<https://blog.thoughtparameters.com/post/nuitka_vs_pyinstaller_python_packaging>
  → **决定：不换工具链**（见 `00-overview.md` 决策 D5）。
- **onedir 优于 onefile**：onefile 每次启动自解压到临时目录，启动更慢且更易被安全软件拦截；`upx=False` 保持不变（UPX 压缩与杀软/签名存在冲突，省量有限）。
- **QQuickStyle 决定必须保留哪些 Controls 样式插件**：样式插件缺失会导致界面无样式或启动失败 → 白名单必须与 `gui_main.py:99` 设置的样式一致，并以实测确认。

## 设计

### 1. 依赖清单归位

`pyproject.toml`：把 `pyinstaller`、`pyinstaller-hooks-contrib` 从 `dependencies` 移到 `[dependency-groups].dev`；随后 `uv lock` + `uv sync`（**禁止手改 `uv.lock`**）。构建时用 `uv run --group dev pyinstaller ...`（或等价的组选择方式）。

### 2. spec 层收敛（三件套 + 逐批实测）

在 `enemyEval.spec` 中，`Analysis` 之后、`COLLECT` 之前插入过滤（形态示意，具体常量以实测清单为准）：

```
_DROP_DLL_PREFIXES = ("Qt6WebEngine", "Qt63D", "Qt6Charts", "Qt6Multimedia", "Qt6Pdf",
                      "Qt6ShaderTools", "Qt6DataVisualization", "Qt6Graphs", "Qt6Quick3D",
                      "Qt6Location", "Qt6Positioning", "Qt6TextToSpeech", "Qt6Sensors",
                      "Qt6Scxml", "Qt6RemoteObjects", "Qt6SerialPort", "Qt6Bluetooth",
                      "Qt6Nfc", "Qt6Sql", "Qt6Designer", "Qt6Help", "Qt6Test", "Qt6QuickTest",
                      "Qt6NetworkAuth", "Qt6AxContainer", "Qt6HttpServer", "Qt6WebChannel",
                      "Qt6WebSockets", "Qt6VirtualKeyboard", "Qt6PdfWidgets")
_DROP_QML_DIRS = ("QtWebEngine", "Qt3D", "QtCharts", "QtQuick3D", "QtMultimedia",
                  "QtDataVisualization", "QtGraphs", "QtLocation", "QtPositioning",
                  "QtTextToSpeech", "QtSensors", "QtScxml", "QtRemoteObjects", "QtSerialPort",
                  "QtBluetooth", "QtNfc", "QtSql", "QtDesigner", "QtHelp", "QtTest",
                  "QtWebChannel", "QtWebSockets", "QtVirtualKeyboard", "Qt5Compat")

analysis.binaries = [...]   # 按前缀剔除
analysis.datas    = [...]   # 剔除 PySide6/qml 下被点名的子目录、translations 里非 zh_CN/en 的条目
```

同时收紧 QML 树来源：`hook-PySide6.QtQml.py` 会收集整棵 `qml`；要彻底避免连带，可在 spec 里对 `analysis.datas` 做**白名单**（只保留 `PySide6/qml/QtQuick`、`QtQuick/Controls`（含当前样式）、`QtQuick/Layouts`、`QtQuick/Window`、`QtQuick/Templates`、`QtQml` 等实测必需项），并在 `hookspath` 无自定义 hook 的前提下验证启动。

**必须保留（经实测确认前不得删除）**：

- `opengl32sw.dll`、`libEGL.dll`/`libGLESv2.dll`/`d3dcompiler_*.dll`（GL 回退链）；
- `plugins/{platforms,imageformats,styles,tls,networkinformation}`；
- Qt6Core/Gui/Widgets/Network/Qml/Quick/QuickControls2/QuickWidgets/OpenGL/OpenGLWidgets 及其依赖；
- `numpy*`、`skia*`、`pydantic_core` 等 Python 侧运行时。

### 3. 制品元信息

- 补 `icon=`（`resource/` 现有资源里选或新增 `.ico`）与 `version=`（指向 PyInstaller version 资源文件；版本值从 `pyproject.toml` 读，与 `build_info.json` 同源，避免漂移）。

### 4. 构建脚本 `scripts/build_release.py`

1. `pyinstaller --noconfirm --clean enemyEval.spec`；
2. 产物校验（缺一即失败）：`dist/enemyEval/enemyEval.exe`、`_internal/build_info.json`、`_internal/gui/qml`、`_internal/resource`；且 `_internal/PySide6/` 下**不应**出现被点名剔除的 DLL/QML 目录；
3. 打 `dist/enemyEval-v{X.Y.Z}-win64.zip`；
4. 输出：zip 体积、解压后体积、SHA256。

### 5. 量化

记录优化前后的 `dist` 体积与"冷启动到 QML `Status.Ready`"耗时（启动日志打点），留待提交时使用。

## 步骤

- [ ] `pyproject.toml` 依赖组归位 → `uv lock` → `uv sync` → 确认 `uv sync` 不再安装 PyInstaller。
- [ ] 批 1（最大且最安全）：剔除 `Qt6WebEngine*` DLL + `qml/QtWebEngine`；重建 + 冒烟。
- [ ] 批 2：剔除 3D / Charts / Multimedia / Pdf / ShaderTools / Quick3D / DataVisualization / Graphs / Sensors / TextToSpeech / Scxml / RemoteObjects / SerialPort / Bluetooth / Nfc / Positioning / Location / Sql / Designer / Help / Test / Qt5Compat；重建 + 冒烟。
- [ ] 批 3：`translations` 只保留 `zh_CN`（与 `en`，若界面/控件需要）。
- [ ] 批 4：`PySide6/qml` 白名单收窄（与 `QQuickStyle` 一致）；重建 + 冒烟。
- [ ] spec 补 `icon` 与 `version`。
- [ ] 新增 `scripts/build_release.py`（构建 → 校验 → zip → 体积/SHA256）。
- [ ] 记录前后数字。
- [ ] 每批的冒烟三件事：启动 → 打开 `data/小杂毛_config.json` → 导出 PNG。

## 非目标

- 不做代码签名（未签名 exe 首次运行的系统警告属预期，不作为缺陷处理）。
- 不换打包工具链（Nuitka / `pyside6-deploy` / cx_Freeze）。
- 不承诺具体瘦身数字（Qt Core/Gui/Qml/Quick 是硬成本）。
- 不精简 `numpy` / `skia`（运行时必需）。
- 不决定 `data/*_config.json` 是否随包分发（单独决策）。
- 不做自更新（任务 04 只提示）。

## 风险与回滚

| 风险 | 处置 |
|---|---|
| 删错二进制 → 启动即崩 | 逐批剔除、每批重建并跑冒烟三件事；崩溃即回退该批 |
| 样式插件缺失 → 界面无样式/控件异常 | QML 白名单与 `QQuickStyle` 对齐，实测确认 |
| 无显卡驱动机器启动失败 | 保留 `opengl32sw.dll` 与 ANGLE 组件 |
| 图像格式插件缺失 → 头像/图片加载失败 | 保留 `plugins/imageformats` 全量 |
| 反复构建耗时 | 每次只动一批，失败批单独回退；构建产物不入库（`dist/`、`build/` 已被忽略） |
| 回滚 | spec 改动集中在过滤段，删除该段即回到当前行为；依赖组回滚为一次 `uv lock` |

## 验收

1. 干净 Windows（无 Python、无 uv）解压 zip → 双击 `enemyEval.exe` → 启动、打开一份配置、导出 PNG 全通。
2. `dist` 内不再包含 `Qt6WebEngineCore.dll` 与被点名剔除的模块；zip 体积与解压后体积有记录（未达标也给实测值）。
3. `uv sync` 后不再安装 PyInstaller。
4. 启动耗时与优化前的实测值并列记录。
