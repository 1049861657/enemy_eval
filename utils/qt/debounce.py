"""预览防抖：延迟按调用频率在 `min_delay` / `max_delay` 之间上浮。

- 频率窗口 1000 ms：窗口内调用数 >5 用 `max_delay`，>2 用两者中值，否则 `min_delay`。
- 单个单次 `QTimer` 复用；新调用重启计时并覆盖前一个回调，故只有最后一次调用会执行。
- 回调在 `QTimer` 所属线程（GUI 主线程）执行；`cleanup()` 停表并丢弃未执行的回调。
"""
import time
from typing import Optional, Callable
from PySide6.QtCore import QTimer


class AdaptiveDebouncer:
    """预览防抖器：延迟规则见模块 docstring；同一实例同时只保留一个待执行回调。"""
    
    def __init__(self, min_delay: int = 50, max_delay: int = 300):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_call_time = 0
        self._call_count = 0
        self._timer: Optional[QTimer] = None
        self._pending_callback: Optional[Callable] = None
        
    def debounce(self, callback: Callable) -> None:
        """登记回调并（重）启动计时；后到者覆盖先到者，回调在 GUI 主线程执行。"""
        current_time = time.time() * 1000  # 毫秒
        
        if self._last_call_time > 0:
            time_diff = current_time - self._last_call_time
            if time_diff < 1000:
                self._call_count += 1
            else:
                self._call_count = 0
        
        self._last_call_time = current_time
        self._pending_callback = callback
        
        if self._call_count > 5:
            delay = self.max_delay
        elif self._call_count > 2:
            delay = (self.min_delay + self.max_delay) // 2
        else:
            delay = self.min_delay
        
        # 重用Timer避免频繁创建
        if self._timer is None:
            self._timer = QTimer()
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self._execute_callback)
        
        if self._timer.isActive():
            self._timer.stop()
        
        self._timer.start(delay)
    
    def _execute_callback(self) -> None:
        if self._pending_callback:
            self._pending_callback()
            self._pending_callback = None
        self._call_count = max(0, self._call_count - 2)
    
    def cleanup(self) -> None:
        if self._timer and self._timer.isActive():
            self._timer.stop()
        self._pending_callback = None