"""
字体管理器 - 处理中文字体加载
"""

import skia
from pathlib import Path
import platform

class FontManager:
    """字体管理器"""
    
    def __init__(self):
        self.chinese_font = None
        self._load_chinese_font()
    
    def _load_chinese_font(self):
        """加载中文字体"""
        system = platform.system()
        
        # Windows系统字体路径
        if system == "Windows":
            font_paths = [
                "C:/Windows/Fonts/simhei.ttf",  # 黑体
                "C:/Windows/Fonts/simsun.ttc",  # 宋体
                "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
                "C:/Windows/Fonts/SIMHEI.TTF",  # 黑体(大写)
            ]
        # macOS系统字体路径
        elif system == "Darwin":
            font_paths = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/Library/Fonts/Arial Unicode MS.ttf",
            ]
        # Linux系统字体路径
        else:
            font_paths = [
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/truetype/arphic/uming.ttc",
            ]
        
        # 尝试加载字体
        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    self.chinese_font = skia.Typeface.MakeFromFile(font_path)
                    if self.chinese_font:
                        print(f"成功加载中文字体: {font_path}")
                        break
                except Exception as e:
                    print(f"字体加载失败 {font_path}: {e}")
                    continue
        
        if not self.chinese_font:
            print("警告: 未能加载中文字体，中文可能显示为方框")
            # 使用默认字体
            self.chinese_font = None
    
    def get_font(self, size: int) -> skia.Font:
        """获取指定大小的中文字体"""
        if self.chinese_font:
            return skia.Font(self.chinese_font, size)
        else:
            # 回退到默认字体
            return skia.Font(None, size)