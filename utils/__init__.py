"""工具层包标记。

不做聚合导出：子模块含 httpx / Qt / Skia，聚合会让导入任一子模块即初始化整包。
调用方直接引用子模块：

    from utils.thread_manager import PrtsFetchThread
    from utils.app_settings_store import current_render_options

分层：`models`（零项目内依赖）← `utils` / `core` / `gui` 单向。
"""