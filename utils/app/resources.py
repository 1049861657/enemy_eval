"""静态资源路径：开发态以仓库根为基准，冻结制品以 PyInstaller 解包目录 `sys._MEIPASS` 为基准。

- `get_resource_path(相对路径)` 返回 posix 风格字符串（Qt 与 Skia 都接受）。
- 开发态基准是本文件的 `parents[2]`（`utils/app/` 上溯两级到仓库根）；目录深度一变必须同步。
- 全局单例 `resource_manager`；只拼路径，不检查存在性、不缓存。
"""

import sys
from pathlib import Path


class ResourceManager:
    """资源基准目录持有者；只拼路径，不检查存在性、不缓存。"""

    def __init__(self):
        try:
            self._base_path = sys._MEIPASS  # PyInstaller 打包后的路径
        except AttributeError:
            # 本文件位于 utils/app/：项目根 = parents[2]（改目录深度必须同步这一行）
            self._base_path = str(Path(__file__).parents[2])  # 开发环境路径

    def get_resource_path(self, relative_path: str) -> str:
        return Path(self._base_path, relative_path).as_posix()

    def get_pic_path(self, pic_name: str) -> str:
        return self.get_resource_path(f"resource/pic/{pic_name}")


resource_manager = ResourceManager()
