# 任务 01：配置加载容错与头像路径可移植

**优先级**：P0　**状态**：已实现，待用户本机验收　**依赖**：无

**影响文件**：`models/enemy_data.py`、新增 `utils/avatar_paths.py`、`gui/card_model.py`、`gui/main_window.py`、`gui/qml_bridge.py`、`gui/qml/Workspace.qml`、`tests/test_models.py`、`tests/test_prts_pipeline_refactor.py`

## 目标

头像文件缺失、或配置被搬动/发送给他人后：配置**仍能打开**、**仍能出图**（头像区显示占位底板）；保存时头像路径尽量写成能随配置一起搬动的形式。

## 现状与内部锚点

| 事实 | 锚点 |
|---|---|
| 非 URL 头像在校验期要求文件存在，否则抛 `ValueError` | `models/enemy_data.py:78-89`（`:87` 为 `Path(v).exists()` 判定） |
| 配置里存的是绝对路径 | `data/小杂毛_config.json` → `E:/pythonProject/enemy_eval/enemy/墟/...` |
| 加载路径把校验异常转成 `FileOperationError`，整份配置打不开 | `gui/card_model.py:140`（`load_from_file`）、`utils/error_handler.py:22` |
| 渲染侧已能降级：文件不存在返回 `None`（在 `.stat()` 之前判定，不会抛） | `core/optimization.py::load_avatar_optimized` |
| 拿不到图只记 warning 并跳过贴图，底板/描边/名字照画 | `core/render/sections/avatar.py` |
| 打开/保存的对话框与落盘 | `gui/main_window.py:180-184`、`:195-209` |
| 现有契约测试含 `avatar_path` 5 例，改校验必须同步 | `tests/test_models.py` |
| `enemy/` 被忽略，别人 clone 后必然缺图 | `.gitignore` 的 `/enemy` |

## 外部调研与出处

- **跨盘相对路径会失败（官方事实）**：`os.path.relpath` 在 Windows 上目标与起点不同盘时抛 `ValueError`；`pathlib.Path.relative_to` 同样对不同盘抛 `ValueError`。→ 必须显式回退绝对路径，不能用 `relpath` 一把梭。
  <https://docs.python.org/3/library/os.path.html>、<https://docs.python.org/3/library/pathlib.html>
- **路径大小写与分隔符差异（官方/社区）**：Windows 上比较路径应按规范化结果处理（`os.path.normcase`），否则仅大小写不同会被当成两个文件。 <https://docs.python.org/3/library/os.path.html#os.path.normcase>
- **校验器的定位（官方文档 + 工程判断）**：Pydantic 文档把 validator 定义为"对输入值做校验/规范化"的钩子，未把文件系统检查列为反模式；但 validator 会在**所有构造路径**执行（含从 PRTS 拉取结果构造、从内存构造）。把环境状态塞进去，等于让"数据合法性"依赖"当前机器状态"——本项目的实测后果是整份配置打不开。结论：环境检查留在加载边界。
  <https://docs.pydantic.dev/latest/concepts/validators/>
- **优先级说明**：客户端文件存在性属于运行期事实（可随时变化），而校验发生在构造期（可能早于/晚于事实变化），二者本就不该合并。

## 设计

### 1. 数据层：校验只认形状

`validate_avatar_path` 规则改为：

- 空值 / `None` → 放行（无头像）；
- URL（`models/media.py::is_url`）→ 校验 scheme + netloc 可解析；
- 其它 → 只要求非空字符串（允许相对路径、允许文件不存在）。

删除 `Path(v).exists()` 与"图片文件不存在"错误。**不再有任何校验期 I/O。**

### 2. 路径层：新增 `utils/avatar_paths.py`（纯函数，无 Qt / 无 skia）

```
to_stored_path(path: str, base_dir: Path) -> str
    源：绝对路径 且 与 base_dir 同盘 → base_dir 相对形式（os.path.relpath）
        跨盘（ValueError）→ 原样返回绝对路径
        URL → 原样
resolve_stored_path(stored: str, base_dir: Path) -> str
    源：相对路径 → (base_dir / stored).resolve()
        绝对路径 / URL → 原样
```

`base_dir` 一律是**配置文件所在目录**（不是 CWD，不是项目根）。两函数互为逆运算，用 `tests` 之外的验收覆盖（见下）。

### 3. 边界层：在读写两端各做一次转换

**落点修正（实现时确定）**：转换落在 `gui/card_model.py::load_from_file` / `save_to_file`，而不是 `gui/main_window.py`。两者同属 GUI 层，但模型侧最贴近文件读写，且任何打开路径（文件对话框、后续任务 02 的"最近打开"）都自动获得同一行为，无需在编排层重复转换。

- **打开**（`load_from_file`）：读 JSON 后把 `avatar_path` 解析为绝对路径 → 内存里的模型始终是"可直接渲染的路径"（预览、渲染、URL 预取零改动）。
- **保存**（`save_to_file`）：落盘前转为存储形式，`base_dir` 取**本次保存到的目录** → "另存为"到别处自洽（同盘转相对，跨盘保留绝对）。
- **编排层**（`gui/main_window.py::_open_file`）只负责提示：加载成功后调用 `_warn_missing_avatar()`。

### 4. 可观测性：缺失只提示一次

加载后若 `avatar_path` 为非 URL 且文件不存在 → `QMLBridge.show_toast("头像文件不存在，已按无头像显示", "warning")` 提示一次。不弹错误对话框、不阻断加载、不修改数据。渲染侧 warning 保留。

**验收反馈修订（2026-09-29）**：吐司模板原本只有"绿色 ✓ / 红色 !"两档、且固定在右上角，于是缺头像这类警示被显示成成功样式且不易发现。改动：

- 吐司新增语气档 `info` / `success` / `warning` / `error`：`messageChanged` 信号携带 tone，QML 按 tone 映射配色与图标（沿用既有主题令牌 `accent` / `success` / `warning` / `danger` 及其 `*Subtle`，未新增主题令牌）；
- 位置由右上角改为**顶部居中**（`topMargin` 仍 64，避开命令栏）；
- 调用点归类：缺头像 = `warning`，「请先生成卡片预览」= `info`，「正在获取 PRTS 数据」= `info`，「已导出」= `success`，字段校验失败 = `error`。

## 步骤

- [x] `models/enemy_data.py`：按上表改 `validate_avatar_path`；删掉存在性检查与对应异常文案（同时移除已无用的 `pathlib.Path` 导入，并更新 `avatar_path` 字段描述）。
- [x] 同步 `tests/test_models.py` 的 `avatar_path` 用例（形状契约：空值/空串放行、URL 合法性、无主机 URL 仍拒、不存在的本地路径与相对路径放行、非 http(s) 前缀按本地路径处理）。
- [x] 新增 `utils/avatar_paths.py`（`to_stored_path` / `resolve_stored_path` 两个纯函数 + 模块 docstring 说明跨盘回退）。
- [x] 头像路径解析：落在 `gui/card_model.py::load_from_file`（相对 → 绝对），替代原计划的 `main_window._open_file`。
- [x] 头像路径转存：落在 `gui/card_model.py::save_to_file`（绝对 → 相对，跨盘回退绝对），替代原计划的 `_save_config`。
- [x] 头像缺失提示（`main_window._warn_missing_avatar` + `_open_file` 调用；toast 一次，不新增对话框类型）。验收反馈修订：吐司加语气档、缺头像走 `warning`、位置改顶部居中。

## 非目标

- 不自动收集/复制图片到配置目录（那是产品决定，未立项）。
- 不迁移历史配置里的绝对路径；下次保存自然转成相对形式。
- 不改渲染侧"URL 只查缓存、从不下载"的约定。
- 不新增"文件选择器记住上次目录"之类的周边功能。

## 风险与回滚

| 风险 | 处置 |
|---|---|
| 放宽校验后放行恶意/垃圾路径 | 只影响显示（占位 + toast + warning），无 I/O、无注入面 |
| 用户只搬配置不搬图片 | 相对关系断 → 与"文件缺失"同一路径：提示 + 占位 |
| 保存到跨盘位置 | `to_stored_path` 回退绝对路径，行为与今天一致（可用但不可搬） |
| 回滚 | 单文件级：恢复 `validate_avatar_path` 与两处转换调用即可；无持久化格式变更 |

## 验收

1. 把 `data/小杂毛_config.json` 复制到别处、并把 `enemy/` 目录改名 → 打开副本**能进编辑态**，头像区显示空底板，toast 提示一次，日志有 warning。
2. 在项目内另存到新目录 → 该 JSON 的 `avatar_path` 为相对路径；把它连同图片目录一起搬到别的盘 → 打开仍显示头像。
3. URL 头像行为不变：加载后仍走预取，预取完成后卡片显示头像。
4. `uv run --no-sync pytest -q` 全绿（`test_models.py` 已按新契约更新）。
