"""应用外壳能力：身份、版本、日志、偏好、更新检查、静态资源。

偏好五分：settings（偏好文件读写与容错，唯一落盘点）、rating_prefs（维度模板）、
ai_prefs（AI 三要素与人设）、render_prefs（渲染选项装配）、update_prefs（版本检查字段）。

契约：不依赖 `utils` 其它子包，也不依赖 `core`；偏好读写是 `utils` 内部共用的底座，
`prts` / `ai` 只读取偏好字段。不参与领域逻辑（数据源、AI 调用、渲染）。
不做聚合导出：调用方直接引用子模块（`from utils.app.version import get_app_version`）。
"""
