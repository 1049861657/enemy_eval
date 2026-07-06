# 批次 3：PRTS 数据管线拆分与异步化

**风险等级**：P0/P1 — 涉及全仓库最大文件（690 行）的拆分，务必在批次 0 测试基础设施就绪后再动手。

## 3.1 GUI 阻塞：PRTS 拉取应改为异步（P0，用户可感知）

- [ ] 位置：`gui/main_window.py:363-393`（`_fetch_prts_data`）同步调用 `utils/prts_mediawiki_pipeline.py::fetch_enemy_data`。
- [ ] 问题：`fetch_enemy_data` 内部两次 HTTP 请求（parse API 超时 22s + imageinfo API 超时 12s）+ 头像下载/Skia 解码全部在主线程执行，最长可阻塞 34 秒；`progress_bar.setRange(0,0)` 只是视觉上的"忙碌动画"，事件循环实际被冻结，Windows 上会被系统标记"未响应"，且无法取消。
- [ ] 修复：仿照 `utils/thread_manager.py::CardGeneratorThread` 的模式，新增 `PrtsFetchThread(QThread)` 包装 `fetch_enemy_data`，通过 `Signal` 回传 `(enemy_data, error_msg)`；`_fetch_prts_data()` 只负责起线程、连接信号、更新状态栏/进度条，不再阻塞调用。
- [ ] 验收：点击"参考 PRTS"输入敌人名称后，GUI 窗口在请求过程中仍可拖动/响应其他操作；网络较慢时可通过关闭窗口或未来增加取消按钮中断（至少不能整体卡死）。

## 3.2 单文件五重职责拆分（P1，改动面大，需测试保护）

- [ ] 位置：`utils/prts_mediawiki_pipeline.py` 全文件（690 行）。
- [ ] 问题：混杂 (1) HTTP/MediaWiki API 请求与 Session 管理、(2) wikitext 手写递归下降解析器、(3) 字段名映射表与业务规则、(4) Pydantic 模型构造与类型强转、(5) Skia 图像解码/缩放/写全局缓存，共 5 类职责；且 (5) 直接 `import skia` 和引用 `core.optimization._GLOBAL_IMAGE_CACHE`，构成 `utils` 反向依赖 `core` 的方向性违规。
- [ ] 拆分方案：
  - [ ] `utils/prts_api_client.py`：只负责 `requests.Session`/HTTP 请求/超时/重试（含 3.3 提到的 Session 复用与重试机制）。
  - [ ] `utils/wiki_template_parser.py`：纯字符串解析（`_extract_template_body`、`_extract_all_template_bodies`、`_parse_template_params` 等），零外部依赖，可完整单元测试（对应批次 0 的测试任务）。
  - [ ] `utils/prts_field_mapping.py`：`LEVEL_KEY_MAP`/`COMMON_KEY_MAP`/`ABNORMAL_MAP` 及 `_map_level_block`/`_map_common_block` 等映射函数。
  - [ ] `utils/prts_enemy_builder.py`：`to_enemy_data` 的 Pydantic 组装逻辑。
  - [ ] 头像预下载/Skia 缓存逻辑（`preload_prts_avatar_image`）移出 `utils`，改为独立的 `core/render/avatar_prefetch.py` 或由调用方（GUI 层，配合 3.1 的 `PrtsFetchThread`）持有，消除 `utils → core` 反向依赖。
- [ ] **跨批次依赖**：批次 1 的方案只解决"渲染线程之间"的并发，不解决"渲染线程 vs 本项新增的 `PrtsFetchThread` 之间"的并发——两者是不同线程，仍可能同时读写 `_GLOBAL_IMAGE_CACHE`。落地 `preload_prts_avatar_image` 迁移时需给该全局 dict 的 get/set 加最小粒度的锁（不需要给整个 `RenderResourceManager` 加锁，只需保护这一个全局缓存）。
- [ ] 拆分后 `utils/prts_mediawiki_pipeline.py` 是否保留作为门面（re-export `fetch_enemy_data` 给外部调用方）视实际 import 复杂度决定，避免所有调用方改动过多。

## 3.3 网络请求重试与重复代码

- [ ] 位置：`utils/prts_mediawiki_pipeline.py` 中 `fetch_enemy_from_prts_mediawiki` 与 `fetch_enemy_from_prts_mediawiki_with_debug` 两个函数 HTTP 请求逻辑（session 创建、headers、请求参数、异常处理）几乎逐行重复。
- [ ] 修复：提取公共的 `_fetch_parse_json(session, page_title, timeout)` 辅助函数供两者复用。
- [ ] 引入 `requests.Session` + `HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.5, status_forcelist=[502,503,504]))`，消除单次网络抖动即整体失败的脆弱性。
- [ ] 超时数值（12.0/22.0/10/30.0 四处不同数值）提到模块顶部命名常量（如 `DEFAULT_TIMEOUT_PARSE`/`DEFAULT_TIMEOUT_IMAGEINFO`），不再散落在函数默认参数里。

## 3.4 wikitext 解析器脆弱点补日志（不改变解析逻辑本身，只补可观测性）

- [ ] 为以下"静默降级"分支补 `logger.debug`/`logger.warning`（保留现有兜底行为，只是不再无声）：
  - `_extract_template_body` 对模板名后字符的判断（假设固定字符集合，遇到全角空格等会静默返回 `None`）。
  - `_SKILL_FIELD_PATTERNS` 正则不匹配时的字段丢弃。
  - `merge_wikitext_enemy` 中 `index` 字段缺失/损坏时兜底为 0 导致多个 levelcontent 合并覆盖。
  - `wiki_skia.py::_css_color` 对不识别颜色名的 fallback。
  - `_render_template_spans` 对未知模板 key 的兜底展示分支。
- [ ] 待批次 0 的测试基础设施就绪后，用真实 PRTS 页面 wikitext 样本建立回归测试集，覆盖上述边界情况。

## 3.5 其他清理

- [ ] `utils/network_image.py:68` 的 `except (URLError, HTTPError, OSError, Exception)`：`Exception` 已覆盖前三者，属冗余，改为 `except (URLError, HTTPError, OSError, ValueError) as e: logger.debug(...); return None`，不再完全静默。
- [ ] `utils/network_image.py:18`（`is_url` 内裸 `except:`）改为 `except ValueError:`（`urlparse` 对畸形字符串通常抛 `ValueError`）。
- [ ] `utils/resource_manager.py:23` 的 `os.path.join(...).replace('\\', '/')` 改为 `Path(self._base_path, relative_path).as_posix()`，更符合标准库语义。

## 验收标准

- `scripts/smoke_mediawiki_api.py`（批次 0 改名后）手动联网跑一遍，确认拆分后行为与拆分前一致（至少覆盖 1-2 个真实敌人条目）。
- GUI 中"参考 PRTS"功能在网络延迟场景下不再冻结窗口。
- `grep -r "from core" utils/` 确认不再有 `utils` 反向导入 `core` 的语句。
