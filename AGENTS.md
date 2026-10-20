# AGENTS.md —— 铁律

本文件是对 AI 助手的**绝对约束**：不是建议，不是记录，不是待办清单。

- **禁止助手自行修改本文件。** 不得增删条目，不得在任务完成后"顺手记一条"，不得把当日改动写进本文件。仅当用户**明确要求**修改时才可动。
- **只改用户当次指令指到的文件**；其余文件（尤其 `AGENTS.md`、`CHANGELOG.md`、`pyproject.toml` 版本号、`uv.lock`）发现问题只**报告**，不动手；文件内自带的撰写约定**不构成动手授权**（`CHANGELOG.md` 只在 `skill://git-commit-release` 场景 A/B 内改）。
- 冲突优先级：用户当次明确指令 > 本文件 > 代码 / 注释 / 既有习惯。
  （用户当次放行的例外**只对当次生效**，不得因此写回本文件。）
- 每条规则只写"必须怎么做"；理由仅在"不写就会被踩"时保留一句。

## 技术栈

Python 3.13 · uv（**勿手改 `uv.lock`**，改依赖后在本机 `uv lock` / `uv sync`）· skia-python · PySide6（QML）· Pydantic + pydantic-settings · httpx[http2] + httpx-retries · structlog · platformdirs · cachetools · Rich（CLI）

## 硬性约束

| # | 约束 |
|---|---|
| 1 | 不为「检查」新增测试用例 |
| 2 | 不重复校验 Pydantic 已验字段；不对内部明确类型的调用堆防御性断言 |
| 3 | 任务末尾不擅自运行 Python 验证；由用户本地运行 |
| 4 | 直接替换：不留兼容层、不留旧名别名、不写迁移说明 |
| 5 | 不做回退式凑合实现 |
|6|import 一律写在文件顶部，禁止函数体中部 import。例外只有两类：`utils/qt/render_task.py` 的 `run`、`utils/qt/prts_task.py` 与 `utils/qt/avatar_task.py` 的 `_pull` 延迟导入 `core`（防循环）；`scripts/` 下独立脚本在 `sys.path` 注入后导入本项目模块，用 `# noqa: E402` 标注|
| 7 | 配置一律 JSON、形状符合 Pydantic。敌人配置 `data/{敌人名称}_config.json`；应用偏好 `platformdirs.user_config_path("牢杰的物种奇遇", appauthor="双老蜂")/app_settings.json`（`utils/app/settings.py`） |
| 8 | GUI 职责分离：界面在 `gui/qml/`、主题 `Theme.qml`；启动期的固定连接集中在 `__init__`（可经其调用的一次性 helper，如 `_connect_signals`），随对象生命周期产生的连接（线程实例、换模型）在其创建处完成，且不得落在可重复路径上 |
| 9 | 私有成员 `_` 前缀；完整类型注解（GUI 尤甚）；导入顺序 标准库 → 第三方 → 本项目 |
| 10 | 长任务走线程；关窗只 `requestInterruption` + `task.cancel()`，**绝不 `terminate`** |
| 11 | 依赖单向 `models ← utils / core / gui`，不得出现反向边（有环即为 bug） |
| 12 | `models` 零项目内依赖（标准库 + Pydantic；媒体来源判定 `models/media.py::is_url`）→ `import models` 在任意导入顺序下必须可用 |
| 13 | `utils/__init__.py` 不做聚合导出（只留文档字符串；聚合会让导入任一子模块就初始化整包）。调用方直接写 `from utils.qt.prts_task import PrtsFetchThread` |
| 14 | `utils` 不得模块级 `import core`（渲染相关只走第 6 条例外）；新增跨包 import 前自证不成环：`python -c "import models"`、`import core`、`import main` 各自必须通过 |
| 15 | 注释 / 文档字符串只写声明性事实（契约、不变量、单位、边界、易错点、副作用），短句、名词语。**不写过程性内容**：改动史、"之前是…"、调试过程、动机叙事、第一人称/时间线 |

## 架构要点

- **对外渲染**：`from core import EnemyCardGenerator`（实现在 `core/render/`，`core/__init__` 只导出它）。唯一绘制入口 `_draw_card(enemy, options)`；`RenderOptions` 由 GUI/CLI 传入，core 不读偏好存储。
- **网络头像**：渲染侧只查全局图像缓存、从不下载，未命中即跳过不画；网络 URL 必须先由 PRTS 拉取线程或 `NetworkAvatarPrefetchThread` 预取（`core/render/avatar_prefetch.py`）。缓存与锁的唯一持有者是 `core/render/image_cache.py`。
- **PRTS**：HTTP 层 `utils/prts/api_client.py`（async `AsyncClient` / 同步 `Client`）；编排 `utils/prts/pipeline.py`（async，resolve → parse → imageinfo **串行**）；GUI 经 `PrtsFetchThread` 复用同一 `AsyncClient`。超时一律 `request_timeout(read)`，四参数写全。
- **gui**：QML 在 `gui/qml/{components,pages,dialogs}/`；Python 编排 `main_window` / `qml_bridge` / `bridge/` / `card_model` / `skill_list_model` / `render_coordinator`（渲染串行化）。QML 可见名与信号只在 `qml_bridge.py` 声明，逻辑在 `gui/bridge/`；预览图 provider 在 `gui/bridge/preview.py`。技能列表走 `QAbstractListModel`；标量 JSON 不含 `skills`。
- **错误**：统一 `utils/errors.py`（`RenderError` / `EnemyEvalException` / `FileOperationError`），展示走 `categorize_error_message`。
- **性能**：图像缓存 `core/render/image_cache.py`（`cachetools.LRUCache` + 锁）；预览防抖 `utils/qt/debounce.py`；长任务 `utils/qt/*_task.py`。
- **文件名**：保存/导出默认名一律 `utils/fs/filenames.py::safe_filename`。

## 目录索引

```
enemy_eval/
├── main.py / gui_main.py # CLI / GUI 入口
├── models/               # 数据层：Pydantic 模型与跨层词表（零项目内依赖）
├── core/                 # 渲染层：绘制、布局、字体、资源复用
│   └── render/           # 卡片绘制实现（sections/ 分区、text/ wiki 文本、primitives/ 图元）
├── utils/                # 工具层：app/ prts/ ai/ net/ qt/ fs/ 子包 + errors.py
├── gui/                  # GUI 层：Qt 编排（bridge/ 域实现）与 QML 界面
│   └── qml/              # Workspace.qml / Theme.qml + components/ pages/ dialogs/ icons/
├── data/                 # 敌人配置 JSON 与 PRTS 调试导出
├── enemy/                # 用户本地敌人资源（git 忽略）
├── example/              # CLI 示例头像（`main.py` 引用）
├── resource/             # 打包用静态资源（启动封面）
├── scripts/              # 人工联网冒烟脚本（不接入 pytest discovery）
├── tests/                # pytest 用例与 conftest（隔离偏好文件与 Qt 平台）
├── todos/                # 历次与在途的改进计划
├── enemy_eval.spec       # PyInstaller 打包入口
├── pyproject.toml        # 依赖与唯一版本号来源
├── CHANGELOG.md          # 发布变更记录
├── uv.lock
└── .agents/skills/       # 助手 skill 定义（如 git-commit-release）
```

## 发版（仅当用户明确要求发版 / release）

1. `CHANGELOG.md`「未发布」整块剪切到新版本节；对照上次 tag 核对完整性。
2. SemVer：AI 只可改 `Y` / `Z`，**禁止改 `X`**（除非用户手写指定）。变化大 `Y+1, Z=0`；变化小 `Z+1`。
3. `pyproject.toml` 的 `[project].version` 与该版本节一致（`utils/app/version.py` 依次取已安装分发包元数据、打包 `build_info.json`、`pyproject.toml`；本仓库未安装为分发包，源码运行读到的就是 `pyproject.toml`）。
4. 提交 `chore: release X.Y.Z`；附注 tag `git tag -a vX.Y.Z -m "release X.Y.Z"`。**未经授权不代为 `git push`。**

## 打包（Windows 参考）

```bash
pyinstaller --noconfirm --clean enemy_eval.spec
```
