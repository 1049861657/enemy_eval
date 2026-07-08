"""
自适应防抖器 - 根据调用频率动态调整延迟
"""
import time
from typing import Optional, Callable
from PySide6.QtCore import QTimer


class AdaptiveDebouncer:
    """自适应防抖器 - 根据调用频率动态调整延迟"""
    
    def __init__(self, min_delay: int = 50, max_delay: int = 300):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_call_time = 0
        self._call_count = 0
        self._timer: Optional[QTimer] = None
        self._pending_callback: Optional[Callable] = None
        
    def debounce(self, callback: Callable) -> None:
        """执行防抖调用"""
        current_time = time.time() * 1000  # 转换为毫秒
        
        # 计算调用频率
        if self._last_call_time > 0:
            time_diff = current_time - self._last_call_time
            if time_diff < 1000:  # 1秒内的频繁调用
                self._call_count += 1
            else:
                self._call_count = 0
        
        self._last_call_time = current_time
        self._pending_callback = callback
        
        # 根据调用频率自适应调整延迟
        if self._call_count > 5:  # 高频调用
            delay = self.max_delay
        elif self._call_count > 2:  # 中频调用
            delay = (self.min_delay + self.max_delay) // 2
        else:  # 低频调用
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
        """执行缓存的回调"""
        if self._pending_callback:
            self._pending_callback()
            self._pending_callback = None
        self._call_count = max(0, self._call_count - 2)  # 逐渐降低频率计数
    
    def cleanup(self) -> None:
        """清理资源"""
        if self._timer and self._timer.isActive():
            self._timer.stop()
        self._pending_callback = None

class FixedDebouncer:
    """固定延迟防抖器。

    封装单次 QTimer 样板：构造时绑定回调与延迟，调用方只需 `schedule()` 重启计时，
    刷新 UI 时调用 `stop()` 取消待触发的回调。
    """

    def __init__(self, parent, callback: Callable, delay_ms: int) -> None:
        self._delay_ms = delay_ms
        self._callback = callback
        self._timer = QTimer(parent)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(callback)

    def schedule(self) -> None:
        """重启计时；若已在计时则重置延迟。"""
        self._timer.start(self._delay_ms)

    def stop(self) -> None:
        """取消待触发的回调（用于 refresh_from_model 等同步写入前）。"""
        if self._timer.isActive():
            self._timer.stop()

    def cleanup(self) -> None:
        """释放资源（可选；QTimer 随 parent 销毁时自动清理）。"""
        self.stop()