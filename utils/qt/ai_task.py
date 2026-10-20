"""AI 评价长任务：AiEvaluateThread。

输入：调用配置、人设、基准数据、敌人快照、revision 序号（构造前由调用方备好快照，线程不读模型）。
产出：evaluationFinished(AiEvaluationResult, revision) 或 evaluationFailed(Exception, revision)。
取消：requestInterruption 后以 50ms 粒度轮询取消在飞请求；绝不 terminate。
线程内禁止：新建或访问 QWidget、写偏好文件。
"""

from __future__ import annotations

import asyncio
from typing import Any

from PySide6.QtCore import QThread, Signal

from models import EnemyData

from ..ai.client import aevaluate
from ..app.ai_prefs import AiRequestConfig


class AiEvaluateThread(QThread):
    """AI 评价线程：在事件循环里跑一次异步请求，结果与异常都经信号回主线程。

    中断轮询落在 50ms 粒度上，关窗即可取消在飞请求；入参为调用方准备的快照，线程不读模型。
    """

    # (AiEvaluationResult, revision) / (Exception, revision)
    evaluationFinished = Signal(object, int)
    evaluationFailed = Signal(object, int)

    def __init__(
        self,
        config: AiRequestConfig,
        persona: str,
        baseline: dict[str, Any],
        current: EnemyData,
        revision: int,
    ) -> None:
        super().__init__()
        self._config = config
        self._persona = persona
        self._baseline = baseline
        self._current = current
        self._revision = revision

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            asyncio.run(self._evaluate())
        except Exception as error:
            if not self.isInterruptionRequested():
                self.evaluationFailed.emit(error, self._revision)

    async def _evaluate(self) -> None:
        task = asyncio.create_task(
            aevaluate(self._config, self._persona, self._baseline, self._current)
        )
        try:
            while not task.done():
                if self.isInterruptionRequested():
                    task.cancel()
                    break
                await asyncio.sleep(0.05)
            result = await task
        except asyncio.CancelledError:
            return
        self.evaluationFinished.emit(result, self._revision)
