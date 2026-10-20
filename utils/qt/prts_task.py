"""PRTS 拉取长任务：PrtsFetchThread。

输入：敌人名称。
产出：fetchFinished(EnemyData | None, str | None 错误文案, dict | None 页面上下文)。
页面上下文供级别切换（整页 wikitext + 级别列表 + 默认级别下标），只随本次导入存在、不落盘。
取消：requestInterruption 后以 50ms 粒度轮询取消在飞 asyncio 任务；绝不 terminate。
线程内禁止：新建或访问 QWidget、写偏好文件。
core.render.avatar_prefetch 延迟导入（`_pull` 内）——头像预下载属渲染层职责。
"""

from __future__ import annotations

import asyncio
from typing import Any

from PySide6.QtCore import QThread, Signal

from ..prts import enemy_builder as builder
from ..prts import pipeline as pipeline


class PrtsFetchThread(QThread):
    """PRTS 数据拉取线程：HTTP 请求 + 头像下载/解码不进主线程，同时带回级别切换所需的页面上下文。"""

    # (Optional[EnemyData], Optional[str] error_msg, Optional[dict] 页面上下文)
    fetchFinished = Signal(object, object, object)

    def __init__(self, enemy_name: str):
        super().__init__()
        self.enemy_name = enemy_name

    def run(self):
        """在后台线程中拉取 PRTS 数据并预下载头像。"""
        try:
            asyncio.run(self._fetch())
        except Exception as e:
            if not self.isInterruptionRequested():
                self.fetchFinished.emit(None, f"获取PRTS数据时发生错误：{str(e)}", None)

    async def _fetch(self) -> None:
        task = asyncio.create_task(self._pull())
        try:
            while not task.done():
                if self.isInterruptionRequested():
                    task.cancel()
                    break
                await asyncio.sleep(0.05)
            await task
        except asyncio.CancelledError:
            return

    async def _pull(self) -> None:
        from core.render.avatar_prefetch import preload_network_avatar_image

        async with pipeline.build_async_client() as client:
            if self.isInterruptionRequested():
                return

            raw, page_bundle = await pipeline.fetch_enemy_from_prts_mediawiki_with_debug(
                self.enemy_name, client=client
            )
            if self.isInterruptionRequested():
                return

            if "error" in raw:
                self.fetchFinished.emit(
                    None,
                    pipeline.error_message_for_raw(raw, self.enemy_name),
                    None,
                )
                return

            clean = builder.strip_debug_keys(raw)
            if clean.get("avatar_path"):
                await preload_network_avatar_image(client, clean["avatar_path"])

            if self.isInterruptionRequested():
                return

            enemy_data = builder.to_enemy_data(clean, self.enemy_name)
            if enemy_data is None:
                self.fetchFinished.emit(None, "PRTS数据格式不兼容，无法导入。", None)
                return

            self.fetchFinished.emit(
                enemy_data, None, self._page_context(clean, page_bundle)
            )

    @staticmethod
    def _page_context(clean: dict[str, Any], page_bundle: dict[str, Any]) -> dict[str, Any]:
        """级别切换所需的页面上下文：级别列表与整页 wikitext。只随本次导入存在，不落盘。"""
        wikitext = str(page_bundle.get("wikitext") or "")
        levels = pipeline.parse_enemy_levels(wikitext)
        return {
            "name": str(clean.get("name") or ""),
            "wikitext": wikitext,
            "levels": [{"index": level.index, "label": level.label} for level in levels],
            "level_index": levels[-1].index if levels else -1,
        }
