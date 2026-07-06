# 批次 1：渲染线程并发与全局单例加锁

**风险等级**：P0 — 当前设计存在两个互相矛盾的决策，是本次审查唯一有实际崩溃/画面损坏风险的问题。渲染线程"排队等待"必须做成异步，不能在 GUI 主线程同步 `wait()`——那会违反 `main_window.py:208` 注释写明的"不在主线程等待线程结束，避免打字时界面卡住"的设计初衷，等于用新的 UI 卡顿换掉并发竞态。下方方案已按这个约束设计。

## 背景

`gui/main_window.py:_generate_card()` 对上一个仍在运行的 `CardGeneratorThread` 只调用 `prev.requestInterruption()`（协作式中断，线程体内仅在少数检查点响应），**不等待**就立即 `start()` 新线程。两个 `QThread` 因此可真实并发执行，各自通过 `get_resource_manager()` 拿到同一个模块级单例 `_global_resource_manager`（`core/optimization.py:391-398`，双检查式初始化本身也无锁）。该单例内部 `_canvas_pool`/`_canvas_in_use`/`_font_cache`/`_text_layout_cache`/`_image_cache`（即 `_GLOBAL_IMAGE_CACHE`）全部是裸 dict/list/set，`acquire_canvas`/`release_canvas`/`get_font`/`get_text_layout` 均无锁保护。

高频编辑触发防抖（200-520ms）时是真实可复现的数据竞争，可能导致：
- dict 并发写入损坏
- 同一个 Canvas/Surface 被两个线程同时视为"空闲"而分配给两方
- 画面撕裂

## 方案：异步串行化渲染线程

不在主线程同步 `wait()`，改为让"排队等待上一个线程结束"这件事本身也是异步的：

- [ ] `CardGeneratorThread` 增加互斥标志或改用一个专职的 `RenderQueueController` 对象：`_generate_card()` 触发时，若上一个线程仍在运行，不立即 `start()` 新线程，而是 `requestInterruption()` 后，把"下一次渲染请求"记录为一个 pending 状态（例如 `self._pending_render = True`），真正的 `start()` 延迟到 `prev.finished` 信号触发的槽函数里执行（复用现有 `_release_finished_render_thread` 的连接点，在其中检查 `_pending_render` 并按最新数据发起新渲染）。
- [ ] 效果：任意时刻只有一个 `CardGeneratorThread` 在运行，无并发访问共享单例的可能，且全程不阻塞主线程——`finished` 信号本身是异步回调，不是同步等待。
- [ ] 需要处理"连续多次输入"的合并：`_pending_render` 只需保留"最新一次"的 `enemy_data` 快照，中间态可丢弃（防抖本身已经做了频率削减，这里只需处理"防抖间隔内恰好有一次渲染还没跑完"的边界情况）。
- [ ] `_orphan_render_threads` 列表不再需要（不会再有多个线程并存），随之删除；`closeEvent` 里等待多个孤儿线程的逻辑简化为只等待唯一的 `generator_thread`。

不采用"保留并发+全局加锁"的方向：加锁会串行化 Canvas 池获取/字体获取/文本布局缓存的读写（这些操作在渲染热路径里调用频繁，见批次 5.1），两个线程实际大部分时间也在互相等待，性能收益和上面的串行化方案相当，但需要在所有共享状态访问点小心维护锁的粒度，复杂度和引入新竞态的风险都更高。当前也没有"多线程同时渲染"的业务需求——预览场景本质是"最新一次编辑覆盖之前所有"，上面的方案完全覆盖。

## 关联清理

- [ ] `core/optimization.py::clear_caches()` 目前全仓库零调用点，是死代码。建议挂到 `main_window.closeEvent` 中调用一次（进程退出前清空，语义清晰、无额外风险）；如果确认无需主动清空，删除该方法。
- [ ] `core/optimization.py::_font_cache` 无容量上限和淘汰策略（对比 `_text_layout_cache`/`_image_cache` 都有基于配置的逐出逻辑），补齐或明确注释为何字体缓存不需要上限（提示：字体缓存 key 是 `(size, id(typeface))` 组合，`size` 种类在本项目内是有限枚举，实际增长上限很低，可以只补注释不补逐出逻辑，避免过度工程）。
- [ ] `image_cache` 的淘汰策略当前是 FIFO"删第一个"而非真正 LRU（命中不更新顺序），与其"LRU 清理"的注释不符。改为真 LRU（`dict.move_to_end` 或 `OrderedDict`）或改注释澄清实际策略。

## 验收标准

- 不依赖"人工快速连续输入、肉眼观察是否卡顿/崩溃"作为竞态验证手段——竞态问题本质上不可靠复现，人工验证通过不代表没有问题，只能作为辅助手段。真正的验收：审查改动后的代码路径，确认任意时刻 `self.generator_thread` 指向的线程只会有一个在 `isRunning()`；可写一个断言/日志在 `_generate_card()` 入口处检查这个不变量，短期跑几百次真实编辑操作观察日志无违反。
- `grep` 确认 `clear_caches`/`_font_cache` 相关改动落地后没有遗留的死代码调用点疑问。
