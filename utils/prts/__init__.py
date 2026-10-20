"""PRTS 数据源链路：HTTP 客户端、管线门面、字段映射、数据组装、wikitext 模板语法。

契约：职责是「从 PRTS 取到 EnemyData」；不发界面事件、不读偏好、不写用户文件。
不做聚合导出：调用方直接引用子模块（`from utils.prts.pipeline import fetch_enemy_data`）。
"""
