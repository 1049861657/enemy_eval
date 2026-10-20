"""应用外壳能力：身份、版本、日志、偏好、更新检查、静态资源。

契约：只被入口（`main.py` / `gui_main.py`）与 `gui` 使用；不参与领域逻辑（数据源、AI、渲染）。
不做聚合导出：调用方直接引用子模块（`from utils.app.version import get_app_version`）。
"""
