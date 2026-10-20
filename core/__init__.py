"""渲染层入口。

唯一对外绘制入口是 `core.render.EnemyCardGenerator`；画布池、字体与文本布局缓存、
图像缓存与处理、计时等内部实现不从此处导出，调用方按需从 `core.render.<模块>` 导入。
"""

from .render import EnemyCardGenerator

__all__ = ["EnemyCardGenerator"]
