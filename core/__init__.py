"""
核心基础逻辑模块
包含卡片渲染、性能优化、字体管理等基础功能
"""

from .renderer import EnemyCardGenerator
from .optimization import (
    RenderResourceManager, 
    ImageProcessor, 
    PerformanceTimer,
    get_resource_manager
)
from .fonts import FontManager

__all__ = [
    'EnemyCardGenerator',
    'RenderResourceManager',
    'ImageProcessor', 
    'PerformanceTimer',
    'get_resource_manager',
    'FontManager'
]