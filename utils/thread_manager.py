"""
卡片生成线程管理器
"""
from typing import Optional
import skia
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage, QPixmap

from core import EnemyCardGenerator
from .error_handler import RenderError


class CardGeneratorThread(QThread):
    """卡片生成线程，避免UI阻塞"""
    
    cardGenerated = Signal(object)  # 生成完成信号，传递QPixmap对象
    errorOccurred = Signal(str)  # 错误信号
    
    def __init__(self, enemy_data, save_to_file=False, output_path=None):
        super().__init__()
        self.enemy_data = enemy_data
        self.save_to_file = save_to_file
        self.output_path = output_path
        
    def run(self):
        """在后台线程中生成卡片 - 增强资源管理"""
        try:
            # 检查是否被请求中断
            if self.isInterruptionRequested():
                return
                
            generator = EnemyCardGenerator()
            
            if self.save_to_file:
                # 保存到文件模式
                output_path = generator.generate_card(self.enemy_data, self.output_path)
                if not self.isInterruptionRequested():
                    self.cardGenerated.emit(output_path)
            else:
                # 内存预览模式 - 优化内存管理
                skia_image = generator.generate_card_image(self.enemy_data)
                
                if self.isInterruptionRequested():
                    return
                
                # 转换为QPixmap - 优化性能
                qpixmap = self._skia_to_qpixmap(skia_image)
                
                if not self.isInterruptionRequested() and qpixmap:
                    self.cardGenerated.emit(qpixmap)
                
        except Exception as e:
            if not self.isInterruptionRequested():
                self.errorOccurred.emit(str(e))
    
    def _skia_to_qpixmap(self, skia_image) -> Optional[QPixmap]:
        """优化的Skia到QPixmap转换"""
        try:
            width = skia_image.width()
            height = skia_image.height()
            
            # 获取图像数据
            image_info = skia.ImageInfo.MakeN32Premul(width, height)
            row_bytes = width * 4
            
            # 优化缓冲区创建
            import array
            pixel_buffer = array.array('B', [0] * (width * height * 4))
            
            # 读取像素数据
            success = skia_image.readPixels(image_info, pixel_buffer, row_bytes, 0, 0)
            if not success:
                raise RenderError("无法读取图像像素数据")
            
            pixels = bytes(pixel_buffer)
            
            # 创建QImage - 修复颜色问题
            qimage = QImage(pixels, width, height, QImage.Format.Format_RGBA8888_Premultiplied)
            # 转换颜色通道顺序 BGRA -> RGBA
            qimage = qimage.rgbSwapped()
            return QPixmap.fromImage(qimage)
            
        except Exception as e:
            self.errorOccurred.emit(f"图像转换失败: {str(e)}")
            return None