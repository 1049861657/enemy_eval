# 01 `utils/` 分子包化与改名

**优先级** P0　**依赖** 无　**回滚** 单 commit

## 目标

`utils/` 从 22 个平铺模块改为 6 个特性子包 + 1 个顶层模块；所有模块名与内容对齐。

## 现状锚点

| 事实 | 证据 |
|---|---|
| `utils/` 22 文件 3279 行，占全仓库 32%，是最大包 | 统计 |
| 内容分 4 类：应用外壳/身份/持久化、PRTS+wiki 解析、AI、Qt/网络/文件胶水 | 模块 docstring 与依赖 |
| 模块名前缀当包用：`prts_*` 4 个、`app_*` 4 个、`ai_*` 3 个、`wiki_*` 2 个 | `ls utils/` |
| `utils/__init__.py` 的 docstring 里写着两个示例导入路径 | `utils/__init__.py:6-7` |
| `utils/network_image.py:41` 反向引用 `utils/prts_api_client.request_timeout` | 导入图 |

## 设计结论

子包划分（不新增 `__init__.py` 聚合导出，保持铁律 13）：

| 子包 | 内容 | 判据 |
|---|---|---|
| `utils/app/` | 应用身份、版本、日志、偏好、更新检查、静态资源 | 只被外壳（`main.py`/`gui_main.py`/`gui`）使用，不参与领域逻辑 |
| `utils/prts/` | PRTS 数据源全链路（HTTP 客户端、管线门面、字段映射、数据组装、wikitext 模板语法） | 同一外部数据源的纵向切片 |
| `utils/ai/` | AI 调用、提示词、基准数据装配 | 同一外部能力的纵向切片 |
| `utils/net/` | 传输策略（超时/重试）与通用图像下载 | 被 PRTS 与渲染两侧共用，必须独立于任一领域（见批次 2） |
| `utils/qt/` | Qt 运行时胶水：防抖与三类长任务线程 | 依赖 PySide6，与纯函数工具隔离 |
| `utils/fs/` | 文件名消毒、头像路径互转 | 文件系统边界 |
| `utils/errors.py` | 跨层错误词表与文案分类 | 被 utils/core/gui/scripts/tests 同时使用，不下沉 |

## 改名映射（批次 1 执行）

> ⚑ 标的三个文件按 D11 留给批次 2 一次搬到位，**批次 1 不动它们**。因此批次 1 结束后，`utils/` 下仍会存在 `app_settings_store.py`、`thread_manager.py`、`network_image.py` 三个扁平模块——这是预期状态，不是漏搬。

| 现路径 | 新路径 | 引用点数 |
|---|---|---|
| `utils/__init__.py` | 同名（**docstring 示例路径改为 `utils.app.settings` / `utils.qt.prts_task`**） | — |
| `utils/error_handler.py` | `utils/errors.py` | 10 |
| `utils/app_identity.py` | `utils/app/identity.py` | 5 |
| `utils/app_version.py` | `utils/app/version.py` | 5 |
| `utils/app_logging.py` | `utils/app/logging.py` | 2 |
| `utils/app_settings_store.py` | ⚑ 批次 2：`utils/app/settings.py` + `rating_prefs.py` + `ai_prefs.py` + `render_prefs.py`（四分） | 10 |
| `utils/update_checker.py` | `utils/app/update_check.py` | 2 |
| `utils/resource_manager.py` | `utils/app/resources.py` | 3 |
| `utils/prts_api_client.py` | `utils/prts/api_client.py` | 4 |
| `utils/prts_mediawiki_pipeline.py` | `utils/prts/pipeline.py` | 2 |
| `utils/prts_enemy_builder.py` | `utils/prts/enemy_builder.py` | 3 |
| `utils/prts_field_mapping.py` | `utils/prts/field_mapping.py` | 4 |
| `utils/wiki_template_parser.py` | `utils/prts/wikitext_templates.py` | 2 |
| `utils/ai_client.py` | `utils/ai/client.py` | 3 |
| `utils/ai_prompt.py` | `utils/ai/prompt.py` | 3 |
| `utils/ai_baseline.py` | `utils/ai/baseline.py` | 2 |
| `utils/network_image.py` | ⚑ 批次 2：`utils/net/image_fetch.py`（策略抽到 `utils/net/transport.py`） | 2 |
| `utils/debouncer.py` | `utils/qt/debounce.py` | 1 |
| `utils/thread_manager.py` | ⚑ 批次 2：`utils/qt/render_task.py` + `prts_task.py` + `avatar_task.py`（三分） | 3 |
| `utils/filenames.py` | `utils/fs/filenames.py` | 3 |
| `utils/avatar_paths.py` | `utils/fs/avatar_paths.py` | 1 |
| `utils/wiki_span_parser.py` | **迁出** `core/render/text/wikitext_spans.py`（批次 3） | 4 |

## 步骤

- [ ] 先跑批次 0 基线（`07` §7.0），基线未落盘不得开搬。
- [ ] 跑引用普查并落盘（附录命令），确认映射表引用点数无遗漏；确认 ⚑ 标的三个文件**不在**本批搬迁范围。
- [ ] 建 6 个子包目录与空 `__init__.py`（每个文件的 docstring 写一句：该子包收什么、不收什么；**不做聚合导出**）。
- [ ] 按映射表用"移动 + 改名"逐个搬迁模块（同一批内一次搬完，不留旧文件、不写兼容别名）。
- [ ] 全量替换导入路径：`from utils.X import` → `from utils.<子包>.Y import`（含 `TYPE_CHECKING` 块、函数内导入、docstring 示例）。
- [ ] 更新 `utils/__init__.py` 的分层说明与示例路径。
- [ ] 核对 `enemyEval.spec`：`sys.path` 注入后的 `from utils.app_identity import APP_AUTHOR, APP_NAME` 改为新路径。
- [ ] 核对 `utils/qt/*` 中函数体内 `import core` 的 3 处延迟导入（铁律 6 例外）随文件迁移仍成立。
- [ ] 跑总验收（`07`），并单独跑 `import models` / `import core` / `import main` 自证无环。
- [ ] 记录「顺带发现」到本文件末尾（不实施）。

## 非目标

- 不拆模块内容（`app_settings_store` 的四分、`thread_manager` 的三分属批次 2）。
- **不搬 ⚑ 标的三个文件**（`app_settings_store` / `thread_manager` / `network_image`）：搬迁与拆分在批次 2 一次完成（D11）。
- 不改任何函数签名、默认值、行为、日志文案。
- 不给子包加 `__all__` 或聚合导出（铁律 13）。

## 风险

| 风险 | 缓解 |
|---|---|
| 漏改相对导入以外的引用（测试、脚本、spec、docstring 示例） | 附录命令按"字符串出现处"而非"导入语句"统计，逐个确认 |
| 把 ⚑ 标的三个文件顺手搬了 → 与批次 2 冲突（同一导入点改两遍） | 步骤里显式声明；普查输出里这三个路径出现即视为本批错误 |
| PyInstaller 打包缺模块 | spec 的 `hiddenimports` 与 `datas` 逐项核对；跑一次打包冒烟 |
| 目录改名后 `# noqa: E402` 例外位置变化（`scripts/` 不受影响） | 本批不动 `scripts/` |

## 验收

1. `grep -rn "from utils\.[a-z_]* import" --include=*.py .` 输出中只剩 `utils.<子包>.<模块>`、`utils.errors`，外加**允许保留**的三个扁平名：`utils.app_settings_store`、`utils.thread_manager`、`utils.network_image`（批次 2 处理）。
2. `uv run python -c "import models"|"import core"|"import main"` 全过。
3. `uv run pytest` 全绿；像素回归 4 组样本 sha256 与基线一致。
4. `pyinstaller --noconfirm --clean enemyEval.spec` 成功，`scripts/build_release.py` 校验通过。

## 执行记录（2026-10-20，会话 1）

**实际搬迁 17 个模块**；映射表 20 行中的 3 个按 D11 留给批次 2（`app_settings_store` / `thread_manager` / `network_image`），`wiki_span_parser` 留给批次 3。

| 结果 | 说明 |
|---|---|
| 子包 | 新建 `utils/{app,prts,ai,qt,fs}/__init__.py`（各含"收什么/不收什么"的 docstring，无聚合导出）；**`utils/net/` 未建**——它的首个模块（`transport.py` / `image_fetch.py`）在批次 2 才迁入，避免留空包 |
| 改名 | `error_handler.py → errors.py`；`:9-11` 的 `resource_manager` 符号名与 `RenderResourceManager` 类名**保持不撞**（批次 3 处理后者） |
| `utils/__init__.py` | 重写为按子包描述新布局；两个示例改为真实存在的 `utils.app.version` / `utils.prts.pipeline` |
| 文档字符串 | 另修 14 处指向旧路径的说明（`utils/prts/*` 的 4 个模块互指 + `tests/test_prts_pipeline_refactor.py` 3 处）；`AGENTS.md` 的 6 处按 D10 不动（已登记 `07` §7.6） |
| `enemyEval.spec` | 仅 1 行：`from utils.app.identity import APP_AUTHOR, APP_NAME` |

**普查覆盖不足的教训（写入执行模板）**：开工前的普查只按"导入语句的模块路径"统计，漏了两类形态，搬迁后由悬空导入检查器抓出并修正——

1. `from . import <旧模块> as x`（`utils/thread_manager.py:14-15`）→ 已改 `from .prts import enemy_builder as builder` / `from .prts import pipeline as pipeline`；
2. 指向**本批未搬迁**模块的相对导入（`utils/ai/client.py:18`、`utils/ai/prompt.py:17` 的 `from .app_settings_store import …`）→ 已改 `from ..app_settings_store …`。

⚠ **批次 2 迁移 `app_settings_store` 时，这两行要反过来再改一次**（`from ..app.settings import …`）；同理 `utils/thread_manager.py:17` 的 `from .app_settings_store import`。这不是重复劳动，是 D11 的必然代价——只有 3 处，且已被本记录点名。

**自检结果（只读检查）**：悬空导入 0、旧模块名残留 0、全部 73 个模块导入冒烟通过、`import models` / `import core` / `import main` / `import gui_main` 通过（铁律 14 自证）、文档路径引用 50 处除 `AGENTS.md` 外全部存在。

**顺带发现（不在本批实施）**

- `pyright` 当前无 venv 配置，报告以未解析第三方为主；2 处既有真实类型错误（`utils/prts/pipeline.py:148`、`tests/test_prts_pipeline_refactor.py:84`）。
- `gui/qml/RatingDisplaySwitch.qml` 的 5 处 `Unqualified access`（缺 `pragma ComponentBehavior: Bound`）——批次 4 处理 QML 时评估。
- `tests/test_prts_pipeline_refactor.py` 名字含批次语义且覆盖 5 类被测对象，批次 5 拆名。

**待用户本机验证**（铁律 3）：`uv run pytest -q`（基线 141 项）、`07` §7.2 的 5 组像素 sha256、`pyinstaller --noconfirm --clean enemyEval.spec` + `scripts/build_release.py`（本批改了 spec，属打包相关批次）。

**搬迁引入的真实缺陷（已修，2 处）**

| 位置 | 缺陷 | 若不修的影响 | 修法 |
|---|---|---|---|
| `utils/app/resources.py:19` | 项目根用 `Path(__file__).parent.parent` 推断 → 搬迁后指向 `<repo>/utils` | `resource/` 下所有路径失效：启动封面与窗口图标、`resource/baseline/jesselton_config.json` 加载失败 → **AI 评价失去基准数据**、打包图标路径异常 | 改 `parents[2]` + 不变量注释（"本文件位于 `utils/app/`，改深度必须同步"） |
| `utils/app/version.py:20,47` | 同上（`build_info.json` 与 `pyproject.toml` 定位） | 源码运行 `get_app_version()` 回落成 **`0.0.0`**（关于窗口、启动日志显示错误版本） | 改 `parents[2]` |

**为什么像素回归抓不到**：渲染走的是 `core/optimization.py` 的 `RenderResourceManager`（与 `utils/app/resources.py` 同名不同物），整条渲染路径不碰资源管理器。这类偏差只能靠"搬迁后核查目录深度假设"发现——已作为步骤 **2c** 写入 `07` §7.1。修复后实测：版本号 `0.5.0`、构建时间 `None`、三个资源路径均存在、AI 基准装配 22 键 `name=杰斯顿·威廉姆斯`。

**已核查无同类风险**：本批未搬迁的 `app_settings_store` / `thread_manager` / `network_image` 内**没有** `Path(__file__)` / `parents[` 深度假设（`grep` 实测），故批次 2 的搬迁不会引入同类偏差。

## 顺带发现

（见上「执行记录」末节）
