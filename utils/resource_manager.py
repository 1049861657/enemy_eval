"""
资源文件管理器
统一管理应用所有资源的加载和访问
"""

import sys
import os
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
        return os.path.join(self._base_path, relative_path).replace('\\', '/')
    
    def get_icon_path(self, icon_name: str) -> str:
        """获取图标路径"""
        return self.get_resource_path(f"resource/ico/{icon_name}")
    
    def get_pic_path(self, pic_name: str) -> str:
        """获取图片路径"""
        return self.get_resource_path(f"resource/pic/{pic_name}")
    
    def get_qss_with_resources(self, qss_content: str) -> str:
        """处理QSS内容，替换资源路径"""
        resource_map = {
            'resource/ico/icons8-sort-up-96.png': self.get_icon_path('icons8-sort-up-96.png'),
            'resource/ico/icons8-sort-down-96.png': self.get_icon_path('icons8-sort-down-96.png'),
            'resource/ico/icons8-expand-arrow-96.png': self.get_icon_path('icons8-expand-arrow-96.png'),
        }
        
        processed_qss = qss_content
        for old_path, new_path in resource_map.items():
            processed_qss = processed_qss.replace(old_path, new_path)
        
        return processed_qss


# 全局实例
resource_manager = ResourceManager()