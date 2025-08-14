"""
字体管理器 - 处理中文字体加载 (Windows专用)
"""

import skia
from pathlib import Path

class FontManager:
    """字体管理器 - Windows版本"""
    
    def __init__(self):
        self.chinese_font = None
        self._load_chinese_font()
    
    def _load_chinese_font(self):
        """加载Windows中文字体"""
        # Windows系统字体路径
        font_paths = [
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            "C:/Windows/Fonts/simsun.ttc",  # 宋体
            "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
            "C:/Windows/Fonts/SIMHEI.TTF",  # 黑体(大写)
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