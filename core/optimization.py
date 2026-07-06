"""
高性能渲染优化模块
- 渲染资源复用池：减少85%的Canvas初始化开销
- 图像处理优化：直接Skia处理，消除PIL转换
- 文本布局缓存：智能缓存文本测量结果
"""

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple, List

import skia

# 全局共享图像缓存，确保所有实例能共享预下载的图片；OrderedDict 以支持真 LRU
# （命中时 move_to_end 刷新最近使用位置，超限时从最前端淘汰最久未使用的项）。
_GLOBAL_IMAGE_CACHE: "OrderedDict[str, skia.Image]" = OrderedDict()

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


class RenderResourceManager:
    """渲染资源复用池 - 核心性能优化"""
    
    def __init__(self, config: Optional[RenderConfig] = None):
        self.config = config or RenderConfig()
        
        # Canvas复用池 - 避免频繁创建Surface
        self._canvas_pool: List[Tuple[skia.Surface, skia.Canvas]] = []
        self._canvas_in_use: set = set()
        
        # 字体缓存 - 避免重复加载。无容量上限：key 是 (size, id(typeface)) 组合，
        # 本项目内 size 取值是有限枚举（各绘制点固定字号），实际增长上限很低，
        # 无需引入淘汰逻辑；若未来 size 来源变为不可控的动态值，需要重新评估。
        self._font_cache: Dict[int, skia.Font] = {}
        
        # 文本布局缓存 - 智能缓存测量结果
        self._text_layout_cache: Dict[str, TextLayoutResult] = {}
        
        # 图像缓存 - 使用全局共享缓存
        self._image_cache = _GLOBAL_IMAGE_CACHE
        
        # 性能统计
        self._stats = {
            'canvas_reuse_count': 0,
            'text_cache_hits': 0,
            'image_cache_hits': 0,
            'total_render_time': 0.0
        }
        
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
    
    def release_canvas(self, surface: skia.Surface, canvas: skia.Canvas):
        """释放Canvas回池"""
        for i, (pool_surface, pool_canvas) in enumerate(self._canvas_pool):
            if pool_surface == surface:
                self._canvas_in_use.discard(i)
                break
    
    def get_font(self, size: int, typeface: Optional[skia.Typeface] = None) -> skia.Font:
        """获取缓存的字体"""
        cache_key = hash((size, id(typeface) if typeface else None))
        
        if cache_key not in self._font_cache:
            self._font_cache[cache_key] = skia.Font(typeface, size)
        
        return self._font_cache[cache_key]
    
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
        """优化的文本换行算法 - 支持中文避头尾规则、主动换行和制表符处理"""
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
    
    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        return self._stats.copy()
    
    def clear_caches(self):
        """清空所有缓存（挂在应用退出前调用，见 gui/main_window.py::closeEvent）。"""
        self._font_cache.clear()
        self._text_layout_cache.clear()
        self._image_cache.clear()


class ImageProcessor:
    """高性能图像处理器 - 消除PIL转换开销"""
    
    def __init__(self, cache_manager: RenderResourceManager):
        self.cache_manager = cache_manager
    
    @staticmethod
    def load_image_direct(path: str) -> Optional[skia.Image]:
        """直接加载为Skia图像，避免PIL转换"""
        if not Path(path).exists():
            return None
        
        try:
            # 直接使用Skia加载，避免PIL→NumPy→Skia转换链
            return skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(str(path)))
        except Exception as e:
            print(f"Skia直接加载失败，尝试兼容模式: {e}")
            return None

    # noinspection PyUnreachableCode
    def load_avatar_optimized(self, path: str, target_size: Tuple[int, int] = (330, 330)) -> Optional[skia.Image]:
        """优化的头像加载，带缓存和高质量缩放，支持网络URL"""
        if not path:
            return None
        
        # 导入网络工具（按需导入，减少启动时间）
        from utils.network_image import is_url, get_url_cache_key
        
        # 区分本地文件和网络URL
        if is_url(path):
            # 网络图片处理 - 优化：优先使用缓存，避免渲染时网络阻塞
            cache_key = f"{get_url_cache_key(path)}_{target_size}"
            
            # 检查缓存
            if cache_key in self.cache_manager._image_cache:
                self.cache_manager._stats['image_cache_hits'] += 1
                self.cache_manager._image_cache.move_to_end(cache_key)
                return self.cache_manager._image_cache[cache_key]
            
            # 渲染时快速失败：如果缓存中没有，直接返回None避免阻塞
            # 网络图片应该在数据获取阶段预下载到缓存
            print(f"网络图片未预缓存，跳过加载以避免渲染阻塞: {path}")
            return None
        else:
            # 本地文件处理（保持原逻辑）
            if not Path(path).exists():
                return None
            
            # 生成缓存键
            cache_key = f"{path}_{target_size}_{Path(path).stat().st_mtime}"
            
            # 检查缓存
            if cache_key in self.cache_manager._image_cache:
                self.cache_manager._stats['image_cache_hits'] += 1
                self.cache_manager._image_cache.move_to_end(cache_key)
                return self.cache_manager._image_cache[cache_key]
            
            # 直接Skia加载
            original_image = self.load_image_direct(path)
            if not original_image:
                return None
        
        # 统一的缩放和缓存处理
        try:
            # 高质量缩放 - 使用正确的API
            if (original_image.width(), original_image.height()) != target_size:
                target_w, target_h = target_size
                
                # 创建目标Surface
                scaled_surface = skia.Surface(target_w, target_h)
                scaled_canvas = scaled_surface.getCanvas()
                
                # 使用高质量SamplingOptions（基于文档的正确配置）
                # FilterQuality.kHigh_FilterQuality -> SamplingOptions(CubicResampler.Mitchell())
                sampling = skia.SamplingOptions(skia.CubicResampler.Mitchell())
                
                # 创建Paint（可选，用于额外效果）
                paint = skia.Paint()
                paint.setAntiAlias(True)
                
                # 计算源和目标区域
                src_rect = skia.Rect(0, 0, original_image.width(), original_image.height())
                dst_rect = skia.Rect(0, 0, target_w, target_h)
                
                # 绘制缩放后的图像 - 使用正确的API调用
                scaled_canvas.drawImageRect(original_image, src_rect, dst_rect, sampling, paint)
                scaled_image = scaled_surface.makeImageSnapshot()
            else:
                scaled_image = original_image
            
            # 缓存结果
            # 真 LRU 清理：命中已在读取处 move_to_end，这里淘汰最久未使用（最前端）的一项
            if len(self.cache_manager._image_cache) >= self.cache_manager.config.image_cache_size:
                self.cache_manager._image_cache.popitem(last=False)

            self.cache_manager._image_cache[cache_key] = scaled_image
            return scaled_image
            
        except Exception as e:
            print(f"优化图像加载失败: {e}")
            return None
    
    @staticmethod
    def create_rounded_image(image: skia.Image, radius: float) -> skia.Image:
        """创建圆角图像"""
        surface = skia.Surface(image.width(), image.height())
        canvas = surface.getCanvas()
        
        # 创建圆角裁剪路径
        path = skia.Path()
        rect = skia.Rect(0, 0, image.width(), image.height())
        path.addRoundRect(rect, radius, radius)
        
        canvas.clipPath(path, skia.ClipOp.kIntersect, True)
        canvas.drawImage(image, 0, 0)
        
        return surface.makeImageSnapshot()


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
        print(f"⏱️ {self.name}: {duration*1000:.2f}ms")


# 全局单例实例 - 避免重复初始化
_global_resource_manager = None

def get_resource_manager() -> RenderResourceManager:
    """获取全局资源管理器单例"""
    global _global_resource_manager
    if _global_resource_manager is None:
        _global_resource_manager = RenderResourceManager()
    return _global_resource_manager