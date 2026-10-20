# 02 `utils/` 内部拆分与传输层抽取

**优先级** P0　**依赖** 批次 1　**回滚** 单 commit（可按小节拆 3 个 commit）

## 目标

把"一个文件装多类职责"和"一个文件装多个长任务"拆开；把被两个领域共用的网络策略抽到中立位置。

## 2.0 先决：三个文件在本批一次搬到位（D11）

批次 1 **未**搬它们（避免同一批导入点改两遍），所以本批必须同时完成"搬迁 + 拆分"：

| 文件 | 终态 | 引用点数 |
|---|---|---|
| `utils/app_settings_store.py` | `utils/app/settings.py` + `rating_prefs.py` + `ai_prefs.py` + `render_prefs.py` | 10 |
| `utils/thread_manager.py` | `utils/qt/render_task.py` + `prts_task.py` + `avatar_task.py` | 3 |
| `utils/network_image.py` | `utils/net/image_fetch.py`（超时策略抽到 `utils/net/transport.py`） | 2 |

搬迁后 `utils/` 下不应再有这三个扁平模块。

**批次 1 留下的引用点（本批必须一并改）**——`app_settings_store`：

| 位置 | 形态 |
|---|---|
| `utils/prts/enemy_builder.py:9` | 绝对：`from utils.app_settings_store import get_rating_names` |
| `utils/ai/client.py:18` | 相对：`from ..app_settings_store import AiRequestConfig`（批次 1 刚从 `.app_settings_store` 调过层级，**本批要再调一次**） |
| `utils/ai/prompt.py:17` | 相对：`from ..app_settings_store import load_app_settings` |
| `utils/thread_manager.py:17` | 相对：`from .app_settings_store import AiRequestConfig` |
| `tests/conftest.py:18-19` | 字符串 patch 目标（`settings_file_path` / `_cached`） |

**目录深度**：这 3 个文件内没有 `Path(__file__)` / `parents[` 深度假设（批次 1 实测），本批搬迁不会引入"项目根偏移"类偏差。

## 2.1 `app/settings.py` 四分

**现状锚点**：`utils/app_settings_store.py` 391 行 / **33 个顶层符号**，同时承担 5 类职责；被 10 个文件引用（`gui/card_model.py`、`gui/main_window.py`、`gui/qml_bridge.py`、`main.py`、`scripts/smoke_ai_review.py`、`tests/test_rating_schema.py`、`utils/ai_client.py`、`utils/ai_prompt.py`、`utils/prts_enemy_builder.py`、`utils/qt/render_task.py`）。

| 新模块 | 内容 | 契约 |
|---|---|---|
| `utils/app/settings.py` | 路径、容忍式 JSON 源、`load_app_settings`、`_write_updates`、最近打开文件读写 | 唯一负责"偏好文件的读写与容错"；失败不抛，回落默认 |
| `utils/app/rating_prefs.py` | 评价维度模板读写（`load_rating_schema` / `save_rating_schema` / 默认维度 / 上限裁剪） | 只动维度模板字段 |
| `utils/app/ai_prefs.py` | AI 三要素读写、Base URL 规范化、密钥明文保存语义 | 只动 AI 字段 |
| `utils/app/render_prefs.py` | `current_render_options()`、`set_rating_radar()` | 偏好 → `models.RenderOptions` 的唯一装配点（GUI/CLI 调用） |

**步骤**
- [ ] 拆出 `settings.py`（先搬，不改逻辑），保持 `AppSettings` 模型不变、字段名不变（偏好文件形状零变化）。
- [ ] 搬维度/ AI / 渲染选项三处封装，调用方改为对应模块。
- [ ] 核对 `_TolerantJsonConfigSettingsSource` 只被 `settings.py` 使用。
- [ ] **同步 `tests/conftest.py` 的两个 monkeypatch 目标**（`utils.app_settings_store.settings_file_path`、`utils.app_settings_store._cached`）到新模块路径——必须与搬迁在同一个 commit；改后单独跑 GUI 测试，并确认真实偏好文件未被写入（见 `07` §7.9）。
- [ ] 验收：偏好文件读写的**往返一致性**用现有测试覆盖（`tests/test_rating_schema.py`）+ 手工打开一份旧偏好（形状不变）。

## 2.2 `qt/render_task.py` / `prts_task.py` / `avatar_task.py` 三分

**现状锚点**：`utils/thread_manager.py` 284 行装 3 个互不相关线程；docstring 只写"卡片生成线程管理器"；函数体内 3 处 `import core`（:36、:118、:201，铁律 6 例外）。

| 新模块 | 内容 | 延迟导入（保持） |
|---|---|---|
| `utils/qt/render_task.py` | `CardGeneratorThread` | `run` 内 `import core` |
| `utils/qt/prts_task.py` | `PrtsFetchThread` | `_pull` 内 `import core` |
| `utils/qt/avatar_task.py` | `NetworkAvatarPrefetchThread` | `_pull` 内 `import core.render.avatar_prefetch` |

**步骤**
- [ ] 三个类各搬一文件，类名不变（`gui/main_window.py`、`gui/render_coordinator.py`、`tests/test_prts_pipeline_refactor.py` 只改导入路径）。
- [ ] 每个文件 docstring 写清：输入（快照 + options）、产出信号与参数、取消语义（`requestInterruption` + `task.cancel()`，绝不 `terminate`）、线程内禁止事项（不碰 QWidget、不写偏好文件）。
- [ ] 修正类名与文件名的对应关系（`CardGeneratorThread` 在 `render_task.py`，属可接受；若判定要更名，需同步 `gui`/`tests`，记入本批）。
- [ ] 验收：`tests/test_prts_pipeline_refactor.py::TestPrtsFetchThread` 等线程测试全绿 + 关窗冒烟（取消路径）。

## 2.3 传输策略抽到 `utils/net/`

**现状锚点**：4 处 HTTP 客户端构造，策略各写一套：

| 模块 | 超时/重试 |
|---|---|
| `utils/prts_api_client.py:41,51,71,82` | `request_timeout(read)` + `httpx-retries.Retry`（唯一有重试的） |
| `utils/network_image.py:41` | 复用 `prts_api_client.request_timeout`（**反向领域依赖**） |
| `utils/ai_client.py:210,231` | 自定 `AI_TIMEOUT`，无重试 |
| `utils/update_checker.py:75` | 自定 `_TIMEOUT`，无重试 |
| `utils/app_settings_store.py` | 见 2.1（本批搬迁与拆分） |

**设计结论**：新增 `utils/net/transport.py`，导出 `request_timeout(read_timeout)`、`build_retry(...)`（或等价的统一重试策略）、`log_http_version(...)`；`prts/api_client.py`、`net/image_fetch.py`、`ai/client.py`、`app/update_check.py` 一律从它取。**本批只搬不改语义**（保持各自的超时数值与重试配置不变），统一策略留作后续判断。

**步骤**
- [ ] 把 `request_timeout` 及重试构造从 `prts/api_client.py` 移到 `utils/net/transport.py`，`prts/api_client.py` 保留薄封装或直接改调用点（二选一，禁止同时存在两套实现）。
- [ ] `network_image.py → net/image_fetch.py` 改为依赖 `net/transport.py`，消除 `utils → utils.prts` 的反向边。
- [ ] `ai_client` / `update_checker` 的超时常量改为引用 `net/transport.py` 的构造函数（数值不变）。
- [ ] 验收：PRTS 联网冒烟脚本（`scripts/smoke_mediawiki_api.py`）与 AI 冒烟脚本（`scripts/smoke_ai_review.py`）在人工联网下仍通过；超时行为与改前一致。

## 2.4 头像链路的边界写清（不搬代码）

**现状锚点**：一个关注点跨 4 文件 2 包 —— `utils/net/image_fetch.py`（下载）→ `core/render/avatar_prefetch.py`（预取编排）→ `core/render/surface_pool.py|image_ops.py`（全局图像缓存）→ `utils/qt/avatar_task.py`（线程）。

**结论**：链路本身合理（谁下载 vs 谁缓存 vs 谁编排分属不同层），问题只是**没有一处写明边界**。本批只在 `core/render/avatar_prefetch.py` 与 `utils/net/image_fetch.py` 的 docstring 里各写一句：下载方不写缓存、缓存方不发网络、渲染侧只读缓存（与铁律"渲染侧只查全局图像缓存、从不下载"对齐），并互相指路。**不改代码逻辑。**

## 非目标

- 不改偏好文件形状、字段名、默认值、容错行为。
- 不统一超时数值、不给 AI/更新检查加重试（属行为变化，本计划禁止）。
- 不改线程语义、不合并三类线程为一个通用线程。

## 风险

| 风险 | 缓解 |
|---|---|
| 偏好四分后"写更新"路径出现两份实现 → 出现读写竞争或覆盖 | 唯一写入函数只留在 `settings.py`，其余三模块只调用它 |
| 线程拆文件后延迟导入位置写错（模块级 `import core`）→ 循环导入 | 拆分后立刻 `uv run python -c "import utils.qt.render_task"` 单独导入自证 |
| 抽出 transport 时改了超时数值 | 逐项对照改前的常量值，写进本批 commit message |
| 测试隔离失效：`conftest.py` 按字符串 patch 旧模块的 `settings_file_path` / `_cached` | 与搬迁同一 commit 内改 conftest；改后核对真实偏好文件 mtime 未变（`07` §7.9） |

## 验收

1. `utils/` 下不再有单文件 >250 行（`ai/client.py` 236、`prts/field_mapping.py` 322 除外——后者是纯映射表，评估后若确为数据表则允许，需在本文件说明）。
2. `grep -rn "import core" utils/` 只命中拆分后的 3 个 `_task` 文件函数体内。
3. 两个联网冒烟脚本人工通过；偏好往返测试全绿；像素回归 4 组一致。

## 执行记录（2026-10-20，会话 2）

**状态**：已实施；本机验证（联网冒烟 / 全量 pytest / 像素回归）待用户执行。

### 实际改动

| 原文件 | 终态 |
|---|---|
| `utils/app_settings_store.py`（390 行 / 33 符号） | `utils/app/settings.py`（223 行：读写容错 + 通用槽 + 最近文件）、`rating_prefs.py`、`ai_prefs.py`、`render_prefs.py`、`update_prefs.py` |
| `utils/thread_manager.py`（284 行 / 5 个线程类） | `utils/qt/{render_task,prts_task,avatar_task,update_task,ai_task}.py`（一文件一线程类） |
| `utils/network_image.py` | `utils/net/image_fetch.py`（超时改取 `utils/net/transport.py`） |
| — | 新增 `utils/net/transport.py`（`build_timeout` / `build_retry_transport` / `log_http_version` + 重试常量） |

调用点共 24 处：`gui/{card_model,main_window,qml_bridge,render_coordinator}.py`、`main.py`、`core/{optimization.py,render/avatar_prefetch.py}`、`utils/{ai/client,ai/prompt,prts/enemy_builder,prts/pipeline,app/update_check}`、`tests/{conftest,test_rating_schema,test_prts_pipeline_refactor}`、`scripts/smoke_ai_review.py`、`models/media.py`（docstring）。

### 与任务书的偏差（4 处，均有证据）

1. **偏好拆 5 个模块而非 4 个**：`settings.py` 若同时装 `update_check_*` / `update_seen_*` 六个写入器是 257 行，破「≤250 行」验收门禁；且任务书未给这六个符号定位。故新增 `utils/app/update_prefs.py`（只写版本检查字段，吞掉写盘失败），`settings.py` 降到 223 行。
2. **线程拆 5 个文件而非 3 个**：现状是 5 个线程类（任务书审计漏计 `UpdateCheckThread`、`AiEvaluateThread`）。已同步修正 `00-overview.md` D6。
3. **`request_timeout` 留在 `prts/api_client.py` 作薄封装**（任务书二选一里的"保留薄封装"）：唯一实现 `build_timeout` 在 `transport.py`；`CONNECT_TIMEOUT` 移入 `transport.py`，`api_client` 转导入 → `tests` / `scripts/smoke_mediawiki_api.py` 的既有导入点零改动。
4. **`_log_http_version` → `transport.log_http_version`**，日志文案由 `"PRTS HTTP version: %s"` 变为 `"HTTP version: %s"`（模块名已由 logger 名体现）。属**可观察文本差异**，无功能影响。

另：原 `_write_updates`（吞掉并记日志）改为公开 `try_update_settings`，并保留 `update_settings`（抛 `FileOperationError`）——两者共用同一落盘点，日志文案不变。

### 验收结果

| 项 | 结果 |
|---|---|
| §7.1 悬空导入 / 旧模块名残留 | 0 / 0（`grep app_settings_store\|thread_manager\|network_image` 全仓库为空） |
| §7.1 全模块导入冒烟 | 71 个模块全通过（`scripts/`、`tests/` 除外） |
| §7.1 铁律 14 自证 | `import models` / `core` / `main` / `gui_main` 全通过 |
| §7.1 代码内文件路径引用 | 缺失 0 处 |
| §7.1 目录深度假设核查 | 仅 `utils/app/{resources,version}.py`（批次 1 已修为 `parents[2]`）与 `scripts/*`（深度 1，`parent.parent` 正确） |
| 验收 1：`utils/` 单文件 ≤250 行 | ✅ 本批拆出的文件全部达标（最大 `utils/app/settings.py` 223）。`utils/` 仍有两处 >250 是既有例外：`wiki_span_parser.py` 469（D3 已定迁入 `core/render/text/`，批次 3）、`prts/field_mapping.py` 321（纯映射表，按验收豁免）。其余接近线者：`ai/client.py` 236、`prts/pipeline.py` 247 |
| 验收 2：`utils` 内 `core` 引用 | ✅ 仅 3 个 task 文件函数体内（`render_task.run` / `prts_task._pull` / `avatar_task._pull`） |
| 偏好往返 + 缓存 + 校验语义冒烟 | ✅ 模板/雷达/AI/人设/最近文件/更新检查六类字段读写闭环；删盘后普通读命中缓存、`force_reload` 才回落默认；空 URL / 空模型名仍抛 `ValueError`；落盘 JSON 字段名与顺序未变 |
| 真实偏好文件隔离（§7.9） | ✅ 跑 `test_rating_schema.py` + `test_prts_pipeline_refactor.py` + `test_models.py`（60 passed）前后，真实偏好文件 mtime/size 完全一致 |
| 目标测试 | ✅ `test_rating_schema.py` + `test_prts_pipeline_refactor.py` 共 31 passed |
| `pyside6-qmllint -I gui/qml` | exit 0（5 Warning + 5 Info，全在既有 `RatingDisplaySwitch.qml`） |

### 待用户执行

`uv run pytest -q`（基线 141 项）、`07` §7.2 五组像素 sha256、两个联网冒烟脚本（`scripts/smoke_mediawiki_api.py`、`scripts/smoke_ai_review.py`）、GUI 人工冒烟（§7.3 第 1–5 条）。

## 顺带发现

（执行时回填，不在本批实施）
