# 批次 1：渲染线程并发与全局单例加锁

**风险等级**：P0 — 当前设计存在两个互相矛盾的决策，是本次审查唯一有实际崩溃/画面损坏风险的问题。渲染线程"排队等待"必须做成异步，不能在 GUI 主线程同步 `wait()`——那会违反 `main_window.py:208` 注释写明的"不在主线程等待线程结束，避免打字时界面卡住"的设计初衷，等于用新的 UI 卡顿换掉并发竞态。下方方案已按这个约束设计。

**执行状态：已完成。** `uv run pytest` 75 个测试全部通过；另跑了针对渲染排队不变量的专项冒烟测试，确认高频连续触发不产生并发线程、不阻塞主线程。

## 背景

`gui/main_window.py:_generate_card()` 对上一个仍在运行的 `CardGeneratorThread` 只调用 `prev.requestInterruption()`（协作式中断，线程体内仅在少数检查点响应），**不等待**就立即 `start()` 新线程。两个 `QThread` 因此可真实并发执行，各自通过 `get_resource_manager()` 拿到同一个模块级单例 `_global_resource_manager`（`core/optimization.py:391-398`，双检查式初始化本身也无锁）。该单例内部 `_canvas_pool`/`_canvas_in_use`/`_font_cache`/`_text_layout_cache`/`_image_cache`（即 `_GLOBAL_IMAGE_CACHE`）全部是裸 dict/list/set，`acquire_canvas`/`release_canvas`/`get_font`/`get_text_layout` 均无锁保护。

高频编辑触发防抖（200-520ms）时是真实可复现的数据竞争，可能导致：
- dict 并发写入损坏
- 同一个 Canvas/Surface 被两个线程同时视为"空闲"而分配给两方
- 画面撕裂

## 方案：异步串行化渲染线程

- [x] `gui/main_window.py::MainWindow`：`__init__` 中移除 `_orphan_render_threads` 列表，新增 `self._pending_render = False` 标志。
- [x] `_generate_card()` 重写为：若 `self.generator_thread` 存在且仍在运行，只调用 `requestInterruption()` + 置位 `_pending_render = True` 并立即返回（不创建新线程对象、不阻塞）；否则直接调用新增的 `_start_render_thread()`。
- [x] 新增 `_start_render_thread()`：承担原 `_generate_card` 里创建/连接信号/启动线程的全部逻辑，并把 `finished` 信号连接到新增的 `_on_render_thread_finished`。
- [x] 新增 `_on_render_thread_finished(thread)`：线程结束后 `deleteLater()`，若 `self.generator_thread is thread` 则清空引用；若 `_pending_render` 为真则清零标志并立即 `_start_render_thread()`（用此刻最新的 `card_model.enemy_data`，天然合并了排队期间的多次编辑）。
- [x] 效果：任意时刻只有一个 `CardGeneratorThread` 在运行，无并发访问共享单例的可能，且全程不阻塞主线程——`finished` 是 Qt 队列连接的异步回调，不是同步等待。
- [x] `_orphan_render_threads` 列表已删除；`closeEvent` 简化为只等待唯一的 `self.generator_thread`。

不采用"保留并发+全局加锁"的方向：加锁会串行化 Canvas 池获取/字体获取/文本布局缓存的读写（这些操作在渲染热路径里调用频繁，见批次 5.1），两个线程实际大部分时间也在互相等待，性能收益和上面的串行化方案相当，但需要在所有共享状态访问点小心维护锁的粒度，复杂度和引入新竞态的风险都更高。当前也没有"多线程同时渲染"的业务需求——预览场景本质是"最新一次编辑覆盖之前所有"，上面的方案完全覆盖。

## 关联清理

- [x] `core/optimization.py::clear_caches()`：挂到 `gui/main_window.py::closeEvent` 中调用一次（进程退出前清空，语义清晰、无额外风险）。同时补上原实现遗漏的 `self._font_cache.clear()`（原来只清 `_text_layout_cache`/`_image_cache`）。
- [x] `core/optimization.py::_font_cache` 补齐注释说明为何不需要容量上限（key 是 `(size, id(typeface))` 组合，本项目内 size 取值有限枚举，实际增长上限很低，无需引入淘汰逻辑）。
- [x] `image_cache`（`_GLOBAL_IMAGE_CACHE`）改用 `collections.OrderedDict` 实现真 LRU：命中读取时 `move_to_end(cache_key)` 刷新最近使用位置（`ImageProcessor.load_avatar_optimized` 的网络图片和本地文件两个命中分支都已补上），写入超限时改用 `popitem(last=False)` 淘汰最久未使用项（原来是 `next(iter(...))` + `del`，等价于永远删"插入顺序最早"的项而非"最久未使用"的项）。
- [x] 顺带修复：`RenderResourceManager.__init__(self, config: RenderConfig = None)` 缺少 `Optional` 标注，已改为 `config: Optional[RenderConfig] = None`（`Optional` 已在文件顶部导入，无需新增 import）。

## 验收标准

- [x] 不依赖人工肉眼观察验证竞态。改为编写专项冒烟脚本：headless `QApplication`（`QT_QPA_PLATFORM=offscreen`）实例化 `MainWindow`，连续调用 `_generate_card()` 20 次模拟高频编辑，用真实 Qt 事件循环（`app.exec()` + 安全超时 `QTimer.singleShot`）驱动到收敛，断言 `_start_render_thread` 实际只被触发 1 次（其余 19 次全部被合并为一次 pending 排队），最终 `generator_thread` 为空、`_pending_render` 为 False、渲染结果 `last_generated_pixmap` 非空。结果符合预期，详见下方执行记录。
- [x] `grep` 确认 `clear_caches` 现在有明确调用点（`gui/main_window.py::closeEvent`），`_font_cache` 已补充注释，均无遗留死代码调用点疑问。

## 执行记录

- 冒烟测试输出：`start_calls=1`（"__init__ 里的初始渲染" 1 次 + "连续 20 次快速调用" 全部被合并排队后只触发 1 次真正重渲染，与手动统计口径一致：`_start_render_thread` 总共只被真正调用过一次，因为第一次调用发生在线程还未启动时直接执行，后续 20 次全被判定为"仍在运行"而排队，线程结束后只统一触发一次）、`settled=True`、`pending=False`、`thread_alive=None`、`last_pixmap_present=True`。全程无并发线程、无主线程阻塞、无残留状态。
- `uv run pytest` 75 个测试全部通过（批次 0 建立的回归测试，本批次未修改任何被其覆盖的纯函数，符合预期不受影响）。
- 未改动 `core/render/generator.py`、`utils/thread_manager.py`：渲染线程内部实现本身没有并发问题，问题完全在 `gui/main_window.py` 的线程编排逻辑，因此只改了编排层。
