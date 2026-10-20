"""渲染资源复用与缓存。

- Canvas 复用池
- 图像加载与缩放（Skia 直读 + 全局图像缓存）
- 文本布局缓存
"""

import hashlib
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple, List

import skia
import structlog
from cachetools import LRUCache

from models.media import is_url
from utils.net.image_fetch import get_url_cache_key

logger = structlog.get_logger(__name__)


@dataclass
class TextLayoutResult:
    """文本布局结果缓存"""
    lines: List[str]
    total_height: float
    max_width: float
    line_height: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class RenderConfig:
    """渲染配置参数"""
    # Canvas参数
    width: int = 1950
    height: int = 1500
    
    # 性能参数
    canvas_pool_size: int = 3
    text_cache_size: int = 100
    image_cache_size: int = 20
    cache_expire_seconds: int = 300  # 5分钟缓存过期


# 全局共享图像缓存；LRUCache 在写入超限时淘汰最久未使用项。
# 渲染线程（CardGeneratorThread）与预取线程（PrtsFetchThread /
# NetworkAvatarPrefetchThread，见 core/render/avatar_prefetch.py）会并发读写，
# 因此只对这一个缓存加锁。
_GLOBAL_IMAGE_CACHE = LRUCache(maxsize=RenderConfig.image_cache_size)
_GLOBAL_IMAGE_CACHE_LOCK = threading.Lock()


class RenderResourceManager:
    """渲染资源复用池：Canvas 池、字体缓存、文本布局缓存、图像缓存。"""
    
    def __init__(self, config: Optional[RenderConfig] = None):
        self.config = config or RenderConfig()
        
        # Canvas 复用池：避免重复创建 Surface
        self._canvas_pool: List[Tuple[skia.Surface, skia.Canvas]] = []
        self._canvas_in_use: set = set()
        
        # 字体缓存：key = (字号, typeface id)；字号为固定枚举，故不设容量上限。
        self._font_cache: Dict[int, skia.Font] = {}
        
        # 文本布局缓存：按文本与字号缓存测量结果
        self._text_layout_cache: Dict[str, TextLayoutResult] = {}
        
        # 图像缓存：与预取线程共享的全局缓存
        self._image_cache = _GLOBAL_IMAGE_CACHE
        
        # 性能统计
        self._stats = {
            'canvas_reuse_count': 0,
            'text_cache_hits': 0,
            'image_cache_hits': 0,
            'total_render_time': 0.0
        }
        
        # 可变高度备用 Surface：只保留最近一次非默认尺寸
        self._variable_surface: Optional[Tuple[int, int, skia.Surface]] = None

        # 初始化Canvas池
        self._init_canvas_pool()
    
    def _init_canvas_pool(self):
        """初始化Canvas复用池"""
        for _ in range(self.config.canvas_pool_size):
            surface = skia.Surface(self.config.width, self.config.height)
            canvas = surface.getCanvas()
            self._canvas_pool.append((surface, canvas))
    
    def acquire_canvas(self) -> Tuple[skia.Surface, skia.Canvas]:
        """获取复用的Canvas"""
        # 优先从池中获取未使用的Canvas
        for i, (surface, canvas) in enumerate(self._canvas_pool):
            if i not in self._canvas_in_use:
                self._canvas_in_use.add(i)
                self._stats['canvas_reuse_count'] += 1
                
                # 清空Canvas但保持配置
                canvas.clear(skia.Color4f(0, 0, 0, 0))
                return surface, canvas
        
        # 池已满，创建新的临时Canvas
        surface = skia.Surface(self.config.width, self.config.height)
        canvas = surface.getCanvas()
        return surface, canvas

    def acquire_variable_canvas(
        self, width: int, height: int
    ) -> Tuple[skia.Surface, skia.Canvas]:
        """按 (width, height) 复用一张备用 Surface；尺寸变化时替换。"""
        cached = self._variable_surface
        if cached is not None and cached[0] == width and cached[1] == height:
            surface = cached[2]
            canvas = surface.getCanvas()
            canvas.clear(skia.Color4f(0, 0, 0, 0))
            self._stats["canvas_reuse_count"] += 1
            return surface, canvas
        surface = skia.Surface(width, height)
        self._variable_surface = (width, height, surface)
        return surface, surface.getCanvas()
    
    def release_canvas(self, surface: skia.Surface, canvas: skia.Canvas):
        """释放Canvas回池"""
        for i, (pool_surface, pool_canvas) in enumerate(self._canvas_pool):
            if pool_surface == surface:
                self._canvas_in_use.discard(i)
                break
    
    def get_font(self, size: int, typeface: Optional[skia.Typeface] = None) -> skia.Font:
        """获取指定 (size, typeface) 的字体。

        返回值经 `makeWithSize()` 克隆而非直接复用缓存对象：调用方（如
        `avatar.py::draw_avatar_section` 经 `_get_optimized_font`）会对返回值
        原地 `setEmbolden(True)`，若直接返回缓存实例会污染同 key 的后续取用者
        （与 `core/fonts.py::FontManager.get_font` 的同类问题一致）。
        """
        cache_key = hash((size, id(typeface) if typeface else None))

        template = self._font_cache.get(cache_key)
        if template is None:
            template = skia.Font(typeface, size)
            self._font_cache[cache_key] = template
        return template.makeWithSize(size)
    
    def get_text_layout(self, text: str, max_width: int, font_size: int, 
                       typeface: Optional[skia.Typeface] = None) -> TextLayoutResult:
        """获取缓存的文本布局"""
        # 生成缓存键
        cache_key = hashlib.md5(
            f"{text}_{max_width}_{font_size}_{id(typeface)}".encode()
        ).hexdigest()
        
        # 检查缓存
        if cache_key in self._text_layout_cache:
            result = self._text_layout_cache[cache_key]
            # 检查是否过期
            if time.time() - result.timestamp < self.config.cache_expire_seconds:
                self._stats['text_cache_hits'] += 1
                return result
            else:
                # 过期清理
                del self._text_layout_cache[cache_key]
        
        # 缓存未命中，重新计算
        font = self.get_font(font_size, typeface)
        lines = self._wrap_text_optimized(text, max_width, font)
        
        # 计算布局信息
        line_height = font_size * 1.2  # 行高系数
        total_height = len(lines) * line_height
        max_actual_width = max((font.measureText(line) for line in lines), default=0)
        
        result = TextLayoutResult(
            lines=lines,
            total_height=total_height,
            max_width=max_actual_width,
            line_height=line_height
        )
        
        # 缓存结果（LRU清理）
        if len(self._text_layout_cache) >= self.config.text_cache_size:
            # 清理最旧的缓存项
            oldest_key = min(self._text_layout_cache.keys(), 
                           key=lambda k: self._text_layout_cache[k].timestamp)
            del self._text_layout_cache[oldest_key]
        
        self._text_layout_cache[cache_key] = result
        return result
    
    def _wrap_text_optimized(self, text: str, max_width: int, font: skia.Font) -> List[str]:
        """文本换行：中文避头尾规则、主动换行符、制表符。"""
        if not text:
            return [""]
        
        # 处理制表符 - 转换为4个空格
        if '\t' in text:
            text = text.replace('\t', '    ')
        
        # 处理主动换行符
        if '\n' in text:
            manual_lines = text.split('\n')
            result_lines = []
            for line in manual_lines:
                if line:
                    result_lines.extend(self._wrap_text_optimized(line, max_width, font))
                else:
                    result_lines.append("")
            return result_lines
        
        if font.measureText(text) <= max_width:
            return [text]
        
        # 避头尾规则定义
        cannot_start_line = "，。！？；、）】｝\"'》』"  # 不能在行首的字符
        cannot_end_line = "\"'（【｛《「"  # 不能在行尾的字符
        
        lines = []
        current_line = ""
        i = 0
        
        while i < len(text):
            char = text[i]
            test_line = current_line + char
            
            # 检查当前字符是否能放在当前行
            if font.measureText(test_line) <= max_width:
                current_line = test_line
                i += 1
            else:
                # 当前字符放不下，需要换行
                if current_line:
                    # 检查避头尾规则
                    final_line = current_line
                    next_char = char
                    
                    # 如果下一个字符不能在行首，尝试将其挤到当前行
                    if next_char in cannot_start_line:
                        # 尝试移动当前行最后的一些字符到下一行
                        if len(current_line) > 1:
                            # 找到合适的断点
                            for j in range(len(current_line) - 1, 0, -1):
                                split_char = current_line[j-1]
                                if split_char not in cannot_end_line:
                                    # 在这里分割
                                    final_line = current_line[:j]
                                    remaining = current_line[j:] + next_char
                                    if font.measureText(remaining) <= max_width:
                                        lines.append(final_line)
                                        current_line = remaining
                                        i += 1
                                        break
                            else:
                                # 找不到合适断点，强制换行
                                lines.append(current_line)
                                current_line = next_char
                                i += 1
                        else:
                            # 当前行只有一个字符，强制换行
                            lines.append(current_line)
                            current_line = next_char
                            i += 1
                    else:
                        # 正常换行
                        lines.append(current_line)
                        current_line = next_char
                        i += 1
                else:
                    # 当前行为空，单个字符就超宽，强制添加
                    current_line = char
                    i += 1
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [""]
    
    def clear_caches(self):
        """清空所有缓存（挂在应用退出前调用，见 gui/main_window.py::closeEvent）。"""
        self._font_cache.clear()
        self._text_layout_cache.clear()
        self._variable_surface = None
        with _GLOBAL_IMAGE_CACHE_LOCK:
            self._image_cache.clear()


class ImageProcessor:
    """图像加载与缩放：Skia 直读 + 全局缓存。"""
    
    def __init__(self, cache_manager: RenderResourceManager):
        self.cache_manager = cache_manager
    
    @staticmethod
    def load_image_direct(path: str) -> Optional[skia.Image]:
        """按路径直读为 Skia 图像；文件不存在或解码失败返回 None。"""
        if not Path(path).exists():
            return None
        
        try:
            return skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(str(path)))
        except Exception as e:
            logger.warning("Skia直接加载失败，尝试兼容模式", error=str(e))
            return None

    # noinspection PyUnreachableCode
    def load_avatar_optimized(self, path: str, target_size: Tuple[int, int] = (330, 330)) -> Optional[skia.Image]:
        """头像加载：本地文件按 mtime 缓存，网络 URL 只读缓存；缩放至 target_size。"""
        if not path:
            return None

        if is_url(path):
            # 网络 URL：只读缓存，未命中即返回 None，不在渲染线程下载
            cache_key = f"{get_url_cache_key(path)}_{target_size}"
            
            with _GLOBAL_IMAGE_CACHE_LOCK:
                cached = self.cache_manager._image_cache.get(cache_key)
                if cached is not None:
                    self.cache_manager._stats['image_cache_hits'] += 1
                    return cached
            
            # 网络头像由预取线程写入缓存（core/render/avatar_prefetch.py）
            logger.warning("网络图片未预缓存，跳过加载以避免渲染阻塞", path=path)
            return None
        else:
            # 本地文件：mtime 参与缓存键
            if not Path(path).exists():
                return None
            
            cache_key = f"{path}_{target_size}_{Path(path).stat().st_mtime}"
            
            with _GLOBAL_IMAGE_CACHE_LOCK:
                cached = self.cache_manager._image_cache.get(cache_key)
                if cached is not None:
                    self.cache_manager._stats['image_cache_hits'] += 1
                    return cached
            
            original_image = self.load_image_direct(path)
            if not original_image:
                return None
        
        try:
            if (original_image.width(), original_image.height()) != target_size:
                target_w, target_h = target_size
                
                scaled_surface = skia.Surface(target_w, target_h)
                scaled_canvas = scaled_surface.getCanvas()
                
                # Mitchell 立方重采样
                sampling = skia.SamplingOptions(skia.CubicResampler.Mitchell())
                
                paint = skia.Paint()
                paint.setAntiAlias(True)
                
                src_rect = skia.Rect(0, 0, original_image.width(), original_image.height())
                dst_rect = skia.Rect(0, 0, target_w, target_h)
                
                scaled_canvas.drawImageRect(original_image, src_rect, dst_rect, sampling, paint)
                scaled_image = scaled_surface.makeImageSnapshot()
            else:
                scaled_image = original_image
            
            with _GLOBAL_IMAGE_CACHE_LOCK:
                self.cache_manager._image_cache[cache_key] = scaled_image
            return scaled_image
            
        except Exception as e:
            logger.warning("优化图像加载失败", error=str(e))
            return None
    


class PerformanceTimer:
    """性能计时器"""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        duration = time.perf_counter() - self.start_time
        logger.debug("性能计时", name=self.name, duration_ms=round(duration * 1000, 2))


# 全局单例实例 - 避免重复初始化
_global_resource_manager = None

def get_resource_manager() -> RenderResourceManager:
    """获取全局资源管理器单例"""
    global _global_resource_manager
    if _global_resource_manager is None:
        _global_resource_manager = RenderResourceManager()
    return _global_resource_manager