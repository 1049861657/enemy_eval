# 批次 3：PRTS 数据管线拆分与异步化

**风险等级**：P0/P1 — 涉及全仓库最大文件（690 行）的拆分，务必在批次 0 测试基础设施就绪后再动手。

**执行状态：已完成。** `uv run pytest` 107 个测试全部通过（此前 88 个 + 本批次新增 19 个）。

## 3.1 GUI 阻塞：PRTS 拉取应改为异步（P0，用户可感知）

- [x] 位置：`gui/main_window.py:363-393`（`_fetch_prts_data`）同步调用 `utils/prts_mediawiki_pipeline.py::fetch_enemy_data`。
- [x] 问题：`fetch_enemy_data` 内部两次 HTTP 请求（parse API 超时 22s + imageinfo API 超时 12s）+ 头像下载/Skia 解码全部在主线程执行，最长可阻塞 34 秒；`progress_bar.setRange(0,0)` 只是视觉上的"忙碌动画"，事件循环实际被冻结，Windows 上会被系统标记"未响应"，且无法取消。
- [x] 修复：新增 `utils/thread_manager.py::PrtsFetchThread(QThread)`，`run()` 内调用 `fetch_enemy_from_prts_mediawiki` + `preload_prts_avatar_image` + `to_enemy_data`，通过 `fetchFinished = Signal(object, object)` 回传 `(EnemyData | None, error_msg | None)`；`_fetch_prts_data()` 只负责起线程、连接信号、更新状态栏/进度条，`_on_prts_fetch_finished`/`_on_prts_thread_finished` 分别处理结果与线程清理。`_reference_prts()` 新增守卫：已有 `prts_fetch_thread` 在运行时拒绝发起新请求（提示"请稍候"），避免并发拉取。`closeEvent` 补充等待 `prts_fetch_thread` 收尾（同 `generator_thread` 的 3 秒超时+terminate 兜底模式）。
- [x] 验收：`uv run python`（headless `QT_QPA_PLATFORM=offscreen`）构造 `MainWindow` 并调用 `close()`，`prts_fetch_thread` 字段与回调方法均存在，`closeEvent` 路径正常退出不挂起；`tests/test_prts_pipeline_refactor.py::TestMainWindowPrtsReferenceDoubleFetchGuard` 验证并发拉取守卫生效。真实网络延迟下的窗口响应性按需用 `scripts/smoke_mediawiki_api.py` 人工冒烟，不纳入本批次自动化验收。



## 3.2 单文件五重职责拆分（P1，改动面大，需测试保护）

- [x] 位置：`utils/prts_mediawiki_pipeline.py` 全文件（690 行）。
- [x] 问题：混杂 (1) HTTP/MediaWiki API 请求与 Session 管理、(2) wikitext 手写递归下降解析器、(3) 字段名映射表与业务规则、(4) Pydantic 模型构造与类型强转、(5) Skia 图像解码/缩放/写全局缓存，共 5 类职责；且 (5) 直接 `import skia` 和引用 `core.optimization._GLOBAL_IMAGE_CACHE`，构成 `utils` 反向依赖 `core` 的方向性违规。
- [x] 拆分方案：
  - [x] `utils/prts_api_client.py`：`build_session()`（Session + headers + `HTTPAdapter(max_retries=Retry(...))`）、`_fetch_parse_json`、`fetch_avatar_imageinfo`，含 3.3 的超时常量与重试机制。
  - [x] `utils/wiki_template_parser.py`：纯字符串解析（`_extract_template_body`、`_extract_all_template_bodies`、`_parse_template_params`），零外部依赖，完整单元测试见 `tests/test_prts_mediawiki_pipeline.py`。
  - [x] `utils/prts_field_mapping.py`：`LEVEL_KEY_MAP`/`COMMON_KEY_MAP`/`ABNORMAL_MAP`、`_map_level_block`/`_map_common_block`/`merge_wikitext_enemy`/技能槽位合并等映射函数与业务规则。
  - [x] `utils/prts_enemy_builder.py`：`to_enemy_data`/`_normalize_skills_payload`/`strip_debug_keys` 的 Pydantic 组装逻辑。
  - [x] 头像预下载/Skia 缓存逻辑（`preload_prts_avatar_image`）移至 `core/render/avatar_prefetch.py`；由 `PrtsFetchThread.run()`（GUI 层线程编排，`utils/thread_manager.py`）在后台线程中调用，`utils` 的 5 个新拆分模块均不再 `import core`（`grep -r "from core|import core" utils/` 仅剩 `thread_manager.py` 两处 `QThread.run()` 内的函数局部延迟导入，与既有 `CardGeneratorThread` 的既定模式一致，不构成模块级反向依赖）。
- [x] **跨批次依赖**：`core/optimization.py` 新增模块级 `_GLOBAL_IMAGE_CACHE_LOCK = threading.Lock()`，`RenderResourceManager.clear_caches`/`ImageProcessor.load_avatar_optimized` 的全部 `_image_cache` 读/写/淘汰路径与 `core/render/avatar_prefetch.py::preload_prts_avatar_image` 的写入路径均已包裹该锁，保护渲染线程（`CardGeneratorThread`）与 PRTS 拉取线程（`PrtsFetchThread`）之间对 `_GLOBAL_IMAGE_CACHE` 的并发访问；未对整个 `RenderResourceManager` 加锁（Canvas 池/字体缓存/文本布局缓存仍只在单一串行化渲染线程内访问）。
- [x] `utils/prts_mediawiki_pipeline.py` 保留为门面：re-export 全部拆分模块的公开符号，新增编排函数 `_enemy_from_parse_response`/`fetch_enemy_from_prts_mediawiki`/`fetch_enemy_from_prts_mediawiki_with_debug`/`fetch_enemy_data`/`fetch_enemy_data_raw`/`error_message_for_raw`（后者是从 `fetch_enemy_data` 提炼的错误码→中文提示映射，供 `PrtsFetchThread` 复用，避免重复实现）。调用方（`gui/main_window.py` 曾经的同步调用、`scripts/smoke_mediawiki_api.py`、`tests/test_prts_mediawiki_pipeline.py`）改动极小：脚本 import 路径不变，测试文件的私有辅助函数 import 路径按新模块位置更新。



## 3.3 网络请求重试与重复代码

- [x] 位置：`utils/prts_mediawiki_pipeline.py` 中 `fetch_enemy_from_prts_mediawiki` 与 `fetch_enemy_from_prts_mediawiki_with_debug` 两个函数 HTTP 请求逻辑（session 创建、headers、请求参数、异常处理）几乎逐行重复。
- [x] 修复：提取公共的 `_fetch_parse_json(session, page_title, timeout)`（`utils/prts_api_client.py`）供两者复用。
- [x] 引入 `requests.Session` + `HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.5, status_forcelist=[502,503,504]))`（`build_session()`），消除单次网络抖动即整体失败的脆弱性。
- [x] 超时数值统一为模块顶部命名常量 `DEFAULT_TIMEOUT_PARSE = 22.0`/`DEFAULT_TIMEOUT_IMAGEINFO = 12.0`（`utils/prts_api_client.py`），不再散落在函数默认参数里。



## 3.4 wikitext 解析器脆弱点补日志（不改变解析逻辑本身，只补可观测性）

- [x] 为以下"静默降级"分支补 `logger.debug`/`logger.warning`（保留现有兜底行为，只是不再无声）：
  - `_extract_template_body`/`_extract_all_template_bodies` 对模板名后字符的判断（`utils/wiki_template_parser.py`）：前缀误匹配、未闭合模板均补 `logger.debug`。
  - `_SKILL_FIELD_PATTERNS` 正则不匹配时的字段丢弃（`utils/prts_field_mapping.py::_skill_slots_from_level_zh`）：形似技能字段但未命中任何模式时补 `logger.debug`。
  - `merge_wikitext_enemy` 中 `index` 字段缺失/损坏时兜底为 0（`utils/prts_field_mapping.py`）：补 `logger.warning`，明确提示"可能导致多个 levelcontent 覆盖顺序错乱"。
  - `wiki_skia.py::_css_color` 对不识别颜色名的 fallback：补 `logger.debug`。
  - `_render_template_spans` 对未知模板 key 的两个兜底展示分支：均补 `logger.debug`。
- [x] ~~用真实 PRTS 页面 wikitext 样本建立回归测试集~~：**明确不做。** 现有 `tests/test_prts_mediawiki_pipeline.py` 的构造边界用例已覆盖解析脆弱点；真实页面抓取样本依赖联网、易随 wiki 改版失效，不纳入本批次与仓库回归网。人工联网确认走 `scripts/smoke_mediawiki_api.py`（按需执行，非 CI）。



## 3.5 其他清理

- [x] `utils/network_image.py` 的 `except (URLError, HTTPError, OSError, Exception)` 改为 `except (URLError, HTTPError, OSError, ValueError) as e: logger.debug(...); return None`，不再完全静默。
- [x] `utils/network_image.py`（`is_url` 内裸 `except:`）改为 `except ValueError:`。
- [x] `utils/resource_manager.py` 的 `os.path.join(...).replace('\\', '/')` 改为 `Path(self._base_path, relative_path).as_posix()`，移除不再需要的 `os` import。



## 验收标准

- [x] `scripts/smoke_mediawiki_api.py`：脚本保留为人工联网冒烟入口（import 结构已验证）；真实联网请求不纳入本批次自动化验收，按需人工执行。
- [x] GUI 中"参考 PRTS"功能不再同步阻塞主线程：`_fetch_prts_data` 已完全异步化，`headless MainWindow` 构造/关闭冒烟通过。
- [x] `grep -r "from core" utils/` 确认：5 个新拆分模块（`prts_api_client`/`wiki_template_parser`/`prts_field_mapping`/`prts_enemy_builder`）与门面 `prts_mediawiki_pipeline.py` 均零 `core` 引用；仅 `thread_manager.py` 内两处 `QThread.run()` 方法体内的函数局部延迟导入保留（`CardGeneratorThread` 的既有模式 + 新增的 `PrtsFetchThread` 沿用同一模式），原始违规点（`prts_mediawiki_pipeline.py` 模块级 `from core.optimization import _GLOBAL_IMAGE_CACHE`）已消除。


## 执行记录

- 新增文件：`utils/prts_api_client.py`、`utils/wiki_template_parser.py`、`utils/prts_field_mapping.py`、`utils/prts_enemy_builder.py`、`core/render/avatar_prefetch.py`。
- 改动文件：`utils/prts_mediawiki_pipeline.py`（690 行瘦身为约 190 行门面）、`utils/thread_manager.py`（新增 `PrtsFetchThread`）、`gui/main_window.py`（`_fetch_prts_data` 异步化 + `_reference_prts` 并发守卫 + `closeEvent` 补充等待）、`core/optimization.py`（新增 `_GLOBAL_IMAGE_CACHE_LOCK` 并包裹全部缓存读写路径）、`utils/network_image.py`、`utils/resource_manager.py`、`utils/wiki_skia.py`（补日志）、`utils/__init__.py`（导出 `PrtsFetchThread`）。
- 测试改动：`tests/test_prts_mediawiki_pipeline.py` 的 import 路径按新模块位置更新（纯函数测试内容不变，仍全部通过）；新增 `tests/test_prts_pipeline_refactor.py`（19 个测试），覆盖 `prts_api_client` 的 session/重试/超时/JSON 拉取/头像查询（全部 mock，不联网）、门面 re-export 身份与错误信息映射、`PrtsFetchThread.run()` 成功/错误/异常三路径、`_GLOBAL_IMAGE_CACHE_LOCK` 跨模块共享同一把锁、`_reference_prts` 并发拉取守卫。
- `uv run pytest` 107 个测试全部通过（此前 88 个 + 本批次新增 19 个），无回归。
- 真实联网冒烟与真实 wikitext 样本回归集：**明确不做进仓库自动化**。离线 mock/构造用例已覆盖本批次验收；需要时人工跑 `scripts/smoke_mediawiki_api.py`。

