"""
资源文件管理器
统一管理应用所有资源的加载和访问
"""

import sys
from pathlib import Path


class ResourceManager:
    """统一的资源管理器"""

    def __init__(self):
        """初始化资源管理器"""
        try:
            self._base_path = sys._MEIPASS  # PyInstaller 打包后的路径
        except AttributeError:
            self._base_path = str(Path(__file__).parent.parent)  # 开发环境路径

    def get_resource_path(self, relative_path: str) -> str:
        """获取资源文件完整路径"""
        return Path(self._base_path, relative_path).as_posix()

    def get_pic_path(self, pic_name: str) -> str:
        """获取图片路径"""
        return self.get_resource_path(f"resource/pic/{pic_name}")


# 全局实例
resource_manager = ResourceManager()
