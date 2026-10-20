"""渲染耗时计时：`_draw_card` 每次绘制包一层，退出时按 debug 级别记一次耗时。"""

from __future__ import annotations

import time

import structlog

logger = structlog.get_logger(__name__)


class PerformanceTimer:
    """性能计时器：毫秒整数，`name` 进日志字段。"""

    def __init__(self, name: str):
        self.name = name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        duration = time.perf_counter() - self.start_time
        logger.debug("性能计时", name=self.name, duration_ms=round(duration * 1000, 2))
