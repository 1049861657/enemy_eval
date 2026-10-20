"""Qt 运行时胶水：防抖与长任务线程。

长任务线程按任务一文件：`render_task`（预览渲染）、`prts_task`（PRTS 拉取）、
`avatar_task`（网络头像补取）、`update_task`（版本检查）、`ai_task`（AI 评价）。

契约：依赖 PySide6；线程类只通过信号回传结果，不碰界面对象、不写偏好文件；取消一律
`requestInterruption` + `task.cancel()`，不使用 `terminate()`。
不做聚合导出：调用方直接引用子模块（`from utils.qt.debounce import AdaptiveDebouncer`）。
"""
