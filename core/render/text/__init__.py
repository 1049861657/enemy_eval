"""渲染域文本子系统：wikitext 解析（`wikitext_spans`）与绘制（`wikitext_renderer`）。

契约：只服务卡片渲染，不解析 PRTS 模板语法（数据源解析见 `utils/prts/wikitext_templates.py`）；
解析口径与绘制口径的共享常量（如问号占位相对宽度）住在 `wikitext_spans`，两处不得各写一份。
不做聚合导出：调用方直接引用子模块（`from core.render.text.wikitext_spans import WikiStyle`）。
"""
