"""Skia 图元：星级（`stars`）与雷达（`radar`）。

与 `core/render/sections/` 的分区绘制区分：本包只画单个图元，不编排版面、不读敌人数据。
不做聚合导出：调用方直接引用子模块（`from core.render.primitives.stars import draw_star`）。
"""
