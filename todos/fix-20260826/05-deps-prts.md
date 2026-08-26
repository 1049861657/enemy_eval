# 批次 5：HTTP 目标栈、依赖审计、导出文件名

**风险等级**：P0 — 唯一 HTTP 客户端；PRTS 可取消。紧接批次 1。

**执行状态：已完成。** 行为对外保持：超时量级、502/503/504 重试、UA/Accept-Language、解析与组装逻辑不变。

## 5.1 换成 httpx（去掉 requests）

- [x] 本机：`uv add "httpx[http2]" httpx-retries`；`uv remove requests`（以及 5.3 的未用包）。
- [x] 重写 `utils/prts_api_client.py`：
  - `build_async_client()` → `httpx.AsyncClient`：`http2=True`，`headers=DEFAULT_HEADERS`，`transport=RetryTransport(transport=AsyncHTTPTransport(http2=True, retries=2), retry=Retry(total=2, backoff_factor=0.5, status_forcelist=(502, 503, 504)))`。
  - 超时：`httpx.Timeout(connect=5.0, read=DEFAULT_TIMEOUT_PARSE)` 为客户端默认；imageinfo / resolve 在单次 `get(..., timeout=Timeout(connect=5.0, read=12|4))` 覆盖 read。
  - 所有 `session.get` 改为 `await client.get`；`raise_for_status` 按现逻辑映射错误字符串，不要把 404 重试掉（不在 status_forcelist 即可）。
  - `aclose()` 必须在成功/失败/取消路径调用（`async with` 优先）。
- [x] 编排层（`prts_mediawiki_pipeline.py`）改为 async：`async def fetch_enemy_data` 等；内部仍 resolve → parse → imageinfo **串行**（有数据依赖）。不要为「看起来并发」而 `gather` 这三步。
- [x] `PrtsFetchThread.run`：`asyncio.run(self._fetch())`。`_fetch` 里 `create_task`；循环 `await asyncio.sleep(0.05)` 检查 `isInterruptionRequested()`，为真则 `task.cancel()`。捕获 `CancelledError` 后安静返回（不弹「获取失败」）。
- [x] `gui/main_window.py::closeEvent`：仍 `requestInterruption` + 短 wait；不再 terminate。
- [x] 头像：`download_image_data` 改为走 httpx（可 sync `Client` 短请求，或 PRTS 线程里 `await client.get` 下载字节）。删除 `urllib.request.urlopen` 路径。`is_url` / `get_url_cache_key` 保留。
- [x] `scripts/smoke_mediawiki_api.py` 改 `httpx.Client`（同步 API 即可），同一 headers/timeout。
- [x] 测试：`tests/test_prts_pipeline_refactor.py` 从 mock `requests.Session` 改为 `httpx.MockTransport` 或 mock `AsyncClient.get`。契约变了，这是允许的测试改动，不要另堆无关用例。
- [x] DEBUG 日志：`response.http_version`（确认 H2 或回落 1.1）。
- [x] 验收：`grep` 产品代码无 `import requests`。本地对一名已知敌人 PRTS 仍填表（人工联网）。拉取中途关窗，约 3s 内退出。smoke 脚本仍可用。

## 5.2 图像 LRU

- [x] `uv add cachetools`。
- [x] `_GLOBAL_IMAGE_CACHE` 改为 `cachetools.LRUCache(maxsize=config.image_cache_size)`；读写仍持现有锁。
- [x] 验收：预缓存头像后预览仍命中；超限淘汰最旧项。

## 5.3 去掉未引用的直接依赖

- [x] `grep` 确认无 `bs4` / `PIL`。
- [x] 移除 `beautifulsoup4`、`pillow`；`numpy` 不再直接声明。
- [x] `gui_main.check_dependencies` 只检查实际导入：skia、pydantic、PySide6、httpx。批次 4 已改为 `uv sync` 并检查前三项；本项补上 httpx。
- [x] 验收：`uv run python -c "from core import EnemyCardGenerator"` 可导入。

## 5.4 导出/保存默认名消毒

- [x] `utils/filenames.py::safe_filename`（`\/:*?"<>|` → `_`，空则 `untitled`）。
- [x] GUI 保存/导出默认名、`generate_card` 无路径时、smoke 脚本共用。
- [x] 验收：名称含 `:` 的敌人，默认文件名合法。
