"""Qt 胶水：防抖与长任务线程，一任务一文件。

线程只通过信号回传；取消用 `requestInterruption` + `task.cancel()`，绝不 `terminate()`。
"""
