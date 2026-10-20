"""工具层包标记。

布局（按特性分子包，不再平铺）：

    app/     身份、版本、日志、偏好、更新检查、静态资源
    prts/    PRTS 数据源链路：客户端、管线、字段映射、数据组装、wikitext 模板语法
    ai/      AI 评价链路：调用层、提示词、基准数据装配
    qt/      Qt 运行时胶水：防抖与长任务线程
    fs/      文件系统边界：文件名消毒、头像路径互转
    errors.py  跨层错误词表与文案分类

不做聚合导出：子模块含 httpx / Qt / Skia，聚合会让导入任一子模块即初始化整包。
调用方直接引用子模块：

    from utils.app.version import get_app_version
    from utils.prts.pipeline import fetch_enemy_data

分层：`models`（零项目内依赖）← `utils` / `core` / `gui` 单向。
"""
