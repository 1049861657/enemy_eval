"""
完全匹配原版设计的敌人评价卡片生成器
"""

import skia
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from models import EnemyData, CardStyle
from font_manager import FontManager

class EnemyCardGenerator:
    """敌人评价卡片生成器 - 完全匹配原版"""
    
    def __init__(self):
        self.width = 650
        self.height = 550
        self.surface = None
        self.canvas = None
        self.font_manager = FontManager()
        
        # 等级颜色主题
        self.grade_colors = {
            'S': (0.85, 0.2, 0.5, 1.0),   # 粉红色
            'A': (0.2, 0.7, 0.9, 1.0),    # 蓝色
            'B': (0.3, 0.8, 0.3, 1.0),    # 绿色
            'C': (0.9, 0.7, 0.2, 1.0),    # 橙色
            'D': (0.6, 0.6, 0.6, 1.0)     # 灰色
        }
        
    def _init_canvas(self):
        """初始化Skia画布与渐变背景"""
        self.surface = skia.Surface(self.width, self.height)
        self.canvas = self.surface.getCanvas()
        
        # 创建渐变背景
        gradient_colors = [
            skia.Color4f(0.95, 0.95, 0.98, 1.0),  # 浅蓝白
            skia.Color4f(0.92, 0.92, 0.95, 1.0)   # 稍深
        ]
        gradient = skia.GradientShader.MakeLinear(
            points=[(0, 0), (self.width, self.height)],
            colors=gradient_colors
        )
        paint = skia.Paint(Shader=gradient)
        self.canvas.drawPaint(paint)
    
    def _draw_avatar_section(self, enemy: EnemyData):
        """绘制左侧方形头像区域"""
        # 绘制头像背景方形
        avatar_rect = skia.Rect(15, 15, 135, 135)
        
        # 阴影效果
        shadow_paint = skia.Paint(Color=skia.Color4f(0, 0, 0, 0.1))
        shadow_rect = skia.Rect(19, 19, 139, 139)
        self.canvas.drawRoundRect(shadow_rect, 8, 8, shadow_paint)
        
        # 主背景
        bg_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 0.95))
        self.canvas.drawRoundRect(avatar_rect, 6, 6, bg_paint)
        
        # 边框
        border_paint = skia.Paint(Color=skia.Color4f(*self.grade_colors.get(enemy.grade, (0.6, 0.6, 0.6, 0.8))))
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(2)
        self.canvas.drawRoundRect(avatar_rect, 6, 6, border_paint)
        
        # 绘制方形头像（优化色彩保真度）
        if enemy.avatar_path and Path(enemy.avatar_path).exists():
            try:
                pil_img = Image.open(enemy.avatar_path)
                pil_img = pil_img.resize((110, 110), Image.Resampling.LANCZOS)  # 使用高质量重采样
                
                # 智能RGBA转换，保持原始色彩
                if pil_img.mode == 'RGB':
                    # RGB转RGBA时添加完全不透明的Alpha通道
                    img_array = np.array(pil_img)
                    # 添加Alpha通道(255表示完全不透明)
                    alpha_channel = np.full((img_array.shape[0], img_array.shape[1], 1), 255, dtype=np.uint8)
                    img_array = np.concatenate([img_array, alpha_channel], axis=2)
                elif pil_img.mode == 'RGBA':
                    # 已经是RGBA，直接使用
                    img_array = np.array(pil_img)
                else:
                    # 其他格式先转RGB再转RGBA
                    pil_img = pil_img.convert('RGB')
                    img_array = np.array(pil_img)
                    alpha_channel = np.full((img_array.shape[0], img_array.shape[1], 1), 255, dtype=np.uint8)
                    img_array = np.concatenate([img_array, alpha_channel], axis=2)
                
                skia_img = skia.Image.fromarray(img_array, skia.kRGBA_8888_ColorType)
                
                # 在方形区域内绘制头像
                img_rect = skia.Rect(20, 20, 130, 130)
                self.canvas.drawImageRect(skia_img, img_rect)
                
            except Exception as e:
                print(f"头像加载失败: {e}")
        
        # 绘制敌人名称（简洁样式，无边框）
        font = self.font_manager.get_font(16)
        font.setEmbolden(True)  # 加粗显示
        paint = skia.Paint(Color=skia.Color4f(0.1, 0.1, 0.1, 1), AntiAlias=True)
        
        # 计算文字居中位置
        text_width = font.measureText(enemy.name)
        text_x = 75 - text_width / 2
        self.canvas.drawString(enemy.name, text_x, 155, font, paint)
    
    def _draw_main_stats_table(self, enemy: EnemyData):
        """绘制主要属性表格形式 - 参考图样式"""
        # 移除外边框，直接绘制表格内容
        
        # 字体设置 - 参考新需求图片的色彩方案
        font_name = self.font_manager.get_font(9)
        font_value = self.font_manager.get_font(11)
        name_paint = skia.Paint(Color=skia.Color4f(0.3, 0.3, 0.3, 1), AntiAlias=True)  # 列名文字稍深
        value_paint = skia.Paint(Color=skia.Color4f(0.1, 0.1, 0.1, 1), AntiAlias=True)  # 值文字更深
        
        # 表格数据（3行布局按新需求）
        attrs_data = [
            [("攻击方式", enemy.attack_type), ("行动方式", enemy.action_type), ("生命回复速度", enemy.hp_recovery_speed), ("地位", enemy.position), ("种类", enemy.category)],
            [("最大生命值", enemy.max_hp), ("攻击力", enemy.attack), ("防御力", enemy.defense), ("法术抗性", enemy.magic_resistance), ("攻击范围半径", enemy.attack_range_radius), ("重量", enemy.weight_level)],
            [("移动速度", enemy.move_speed), ("攻击间隔", enemy.attack_interval), ("损伤抗性", enemy.damage_resistance), ("元素抗性", enemy.element_resistance), ("基础嘲讽等级", enemy.base_taunt_level), ("目标价值", enemy.target_value)]
        ]
        
        # 表格参数 - 智能动态布局，与其他框宽度一致
        start_x = 160  # 与描述框和异常抗性框对齐
        start_y = 60
        cell_height = 26  # 再次增加行高避免重叠
        total_width = 630 - 160  # 与其他框相同的总宽度
        
        # 动态计算每行的列宽，确保所有行总宽度一致
        def calculate_optimal_widths(row_data, available_width):
            """根据内容长度智能分配列宽，确保总宽度一致"""
            if not row_data:
                return []
            
            # 计算每列内容的最小宽度需求
            min_widths = []
            for name, value in row_data:
                name_len = len(str(name))
                value_len = len(str(value))
                # 估算最小宽度：较长文本需要更多空间
                min_width = max(name_len, value_len) * 8 + 10  # 8px每字符+边距
                min_widths.append(min_width)
            
            # 确保总宽度等于available_width
            total_min_width = sum(min_widths)
            if total_min_width > available_width:
                # 按比例缩放，确保总宽度不超过available_width
                scale = available_width / total_min_width
                scaled_widths = [int(w * scale) for w in min_widths]
                # 处理舍入误差，确保总宽度准确
                diff = available_width - sum(scaled_widths)
                if diff > 0:
                    scaled_widths[-1] += diff  # 将剩余像素分给最后一列
                return scaled_widths
            else:
                # 平均分配剩余空间，确保总宽度等于available_width
                extra_space = available_width - total_min_width
                extra_per_col = extra_space // len(row_data)
                remainder = extra_space % len(row_data)
                
                final_widths = []
                for i, w in enumerate(min_widths):
                    width = w + extra_per_col
                    if i < remainder:  # 将余数分给前几列
                        width += 1
                    final_widths.append(width)
                return final_widths
        
        # 网格和背景paint
        grid_paint = skia.Paint(Color=skia.Color4f(0.8, 0.8, 0.8, 1))
        grid_paint.setStyle(skia.Paint.kStroke_Style)
        grid_paint.setStrokeWidth(1)
        
        # 列名背景色 - 参考新需求图片的浅灰色背景
        header_bg_paint = skia.Paint(Color=skia.Color4f(0.94, 0.94, 0.94, 1))
        
        # 绘制表格内容 - 使用智能动态布局
        for row_idx, row_data in enumerate(attrs_data):
            y = start_y + row_idx * cell_height
            
            # 为每行计算最优列宽
            row_widths = calculate_optimal_widths(row_data, total_width)
            
            current_x = start_x
            for col_idx, (name, value) in enumerate(row_data):
                cell_width = row_widths[col_idx]
                x = current_x
                cell_rect = skia.Rect(x, y, x + cell_width, y + cell_height)
                
                # 绘制列名区域背景（上半部分）
                header_rect = skia.Rect(x, y, x + cell_width, y + cell_height // 2)
                self.canvas.drawRect(header_rect, header_bg_paint)
                
                # 绘制单元格边框
                self.canvas.drawRect(cell_rect, grid_paint)
                
                # 绘制属性名（上半部分，居中对齐）
                name_width = font_name.measureText(name)
                name_x = x + (cell_width - name_width) / 2
                self.canvas.drawString(name, name_x, y + 10, font_name, name_paint)
                
                # 绘制属性值（下半部分，居中对齐）
                value_str = str(value) if isinstance(value, (int, str)) else f"{value:.1f}"
                value_width = font_value.measureText(value_str)
                value_x = x + (cell_width - value_width) / 2
                self.canvas.drawString(value_str, value_x, y + 23, font_value, value_paint)
                
                # 移动到下一列
                current_x += cell_width
    
    def _draw_unified_info_section(self, enemy: EnemyData):
        """绘制统一信息框 - 合并描述框、主要属性框和异常抗性框"""
        
        # 计算描述区域的动态高度
        desc_lines = self._wrap_text(enemy.brief_description, 450, 11)  # 450px可用宽度
        desc_height = max(25, len(desc_lines) * 16 + 10)  # 每行16px高度+10px底部边距
        
        # 计算总高度：描述高度 + 表格高度(3*28) + 异常抗性高度(25)
        total_height = desc_height + 84 + 25
        
        # 整体信息框区域 - 动态高度
        info_rect = skia.Rect(160, 20, 630, 20 + total_height)
        
        # 主背景
        bg_paint = skia.Paint(Color=skia.Color4f(0.98, 0.98, 0.98, 0.95), AntiAlias=True)
        self.canvas.drawRoundRect(info_rect, 4, 4, bg_paint)
        
        # 主边框
        border_paint = skia.Paint(Color=skia.Color4f(0.8, 0.8, 0.8, 0.9), AntiAlias=True)
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(1)
        self.canvas.drawRoundRect(info_rect, 4, 4, border_paint)
        
        # 1. 绘制黑色描述栏 - 动态高度
        header_rect = skia.Rect(160, 20, 630, 20 + desc_height)
        header_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)
        self.canvas.drawRoundRect(header_rect, 4, 4, header_paint)
        
        # 描述栏下半部分遮盖圆角（除了底部）
        if desc_height > 25:
            header_bottom = skia.Rect(160, 32, 630, 20 + desc_height - 4)
            self.canvas.drawRect(header_bottom, header_paint)
        else:
            header_bottom = skia.Rect(160, 32, 630, 20 + desc_height)
            self.canvas.drawRect(header_bottom, header_paint)
        
        # 描述文字内容 - 多行显示，修复重叠问题
        desc_font = self.font_manager.get_font(11)
        desc_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 1), AntiAlias=True)
        for i, line in enumerate(desc_lines):
            y_pos = 35 + i * 16  # 增加行间距到16px
            self.canvas.drawString(line, 165, y_pos, desc_font, desc_paint)
        
        # 2. 绘制主要属性表格区域 - 紧贴描述栏
        table_start_y = 20 + desc_height
        self._draw_unified_stats_table(enemy, table_start_y)
        
        # 3. 绘制底部异常抗性区域 - 紧贴表格
        resist_start_y = table_start_y + 84  # 3行表格高度84px
        self._draw_bottom_abnormal_resistances(enemy, resist_start_y)
    
    def _draw_unified_stats_table(self, enemy: EnemyData, start_y: int):
        """在统一信息框中绘制主要属性表格"""
        
        # 表格数据（3行布局按新需求）- 修复第一行缺失地位和种类
        attrs_data = [
            [("攻击方式", enemy.attack_type), ("行动方式", enemy.action_type), ("生命自回速度", enemy.hp_recovery_speed), ("地位", enemy.position), ("种类", enemy.category)],
            [("最大生命值", enemy.max_hp), ("攻击力", enemy.attack), ("防御力", enemy.defense), ("法术抗性", enemy.magic_resistance), ("攻击范围半径", enemy.attack_range_radius), ("重量", enemy.weight_level)],
            [("移动速度", enemy.move_speed), ("攻击间隔", enemy.attack_interval), ("损伤抗性", enemy.damage_resistance), ("元素抗性", enemy.element_resistance), ("基础嘲讽等级", enemy.base_taunt_level), ("目标价值", enemy.target_value)]
        ]
        
        # 表格参数 - 调整以与大边框无缝贴合
        start_x = 160  # 与大边框对齐
        cell_height = 28
        total_width = 470  # 统一信息框内的可用宽度，与大边框对齐
        
        # 字体设置 - 参考新需求图优化
        font_name = self.font_manager.get_font(9)
        font_name.setEmbolden(True)  # 列名加粗
        font_value = self.font_manager.get_font(10)
        name_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)  # 列名文字更深
        value_paint = skia.Paint(Color=skia.Color4f(0.1, 0.1, 0.1, 1), AntiAlias=True)
        
        # 网格和背景paint
        grid_paint = skia.Paint(Color=skia.Color4f(0.85, 0.85, 0.85, 1), AntiAlias=True)
        grid_paint.setStyle(skia.Paint.kStroke_Style)
        grid_paint.setStrokeWidth(0.5)
        
        # 列名背景色 - 参考新需求图的浅蓝色调
        header_bg_paint = skia.Paint(Color=skia.Color4f(0.90, 0.94, 0.98, 1), AntiAlias=True)
        
        # 绘制表格内容
        for row_idx, row_data in enumerate(attrs_data):
            y = start_y + row_idx * cell_height
            
            # 为每行计算最优列宽
            row_widths = self._calculate_optimal_widths(row_data, total_width)
            
            current_x = start_x
            for col_idx, (name, value) in enumerate(row_data):
                cell_width = row_widths[col_idx]
                x = current_x
                cell_rect = skia.Rect(x, y, x + cell_width, y + cell_height)
                
                # 绘制列名区域背景（上半部分）
                header_rect = skia.Rect(x, y, x + cell_width, y + cell_height // 2)
                self.canvas.drawRect(header_rect, header_bg_paint)
                
                # 绘制单元格边框
                self.canvas.drawRect(cell_rect, grid_paint)
                
                # 绘制属性名（上半部分，居中对齐）
                name_width = font_name.measureText(name)
                name_x = x + (cell_width - name_width) / 2
                self.canvas.drawString(name, name_x, y + 10, font_name, name_paint)
                
                # 绘制属性值（下半部分，居中对齐）
                value_str = str(value) if isinstance(value, (int, str)) else f"{value:.1f}"
                value_width = font_value.measureText(value_str)
                value_x = x + (cell_width - value_width) / 2
                self.canvas.drawString(value_str, value_x, y + 23, font_value, value_paint)
                
                # 移动到下一列
                current_x += cell_width
    
    def _draw_bottom_abnormal_resistances(self, enemy: EnemyData, start_y: int):
        """在统一信息框底部绘制异常抗性表格"""
        
        # 表格区域
        table_y = start_y
        table_height = 25
        
        # 左侧列头区域（异常抗性） - 与大边框对齐
        header_width = 80
        header_rect = skia.Rect(160, table_y, 160 + header_width, table_y + table_height)
        
        # 右侧内容区域 - 与大边框对齐
        content_rect = skia.Rect(160 + header_width, table_y, 630, table_y + table_height)
        
        # 字体设置
        font = self.font_manager.get_font(10)
        font.setEmbolden(True)  # 异常抗性列头也加粗
        header_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)  # 列头文字更深
        text_paint = skia.Paint(Color=skia.Color4f(0.3, 0.3, 0.3, 1), AntiAlias=True)
        
        # 表格边框画笔
        grid_paint = skia.Paint(Color=skia.Color4f(0.85, 0.85, 0.85, 1), AntiAlias=True)
        grid_paint.setStyle(skia.Paint.kStroke_Style)
        grid_paint.setStrokeWidth(0.5)
        
        # 列头背景 - 使用与主表格一致的背景色
        header_bg_paint = skia.Paint(Color=skia.Color4f(0.90, 0.94, 0.98, 1), AntiAlias=True)
        self.canvas.drawRect(header_rect, header_bg_paint)
        
        # 绘制表格边框
        self.canvas.drawRect(header_rect, grid_paint)  # 左侧列头边框
        self.canvas.drawRect(content_rect, grid_paint)  # 右侧内容边框
        
        # 绘制分隔线（左右分隔）
        separator_x = 160 + header_width
        separator_line = skia.Path()
        separator_line.moveTo(separator_x, table_y)
        separator_line.lineTo(separator_x, table_y + table_height)
        self.canvas.drawPath(separator_line, grid_paint)
        
        # 列头文字 - 移除盾牌图标，简化显示
        self.canvas.drawString("异常抗性", 170, table_y + 16, font, header_paint)
        
        # 根据abnormal_resistances动态显示抗性内容
        active_resistances = []
        for resistance_name, value in enemy.abnormal_resistances.items():
            if value == 1:  # 只显示值为1的抗性
                active_resistances.append(resistance_name)
        
        if active_resistances:
            resist_text = " · ".join(active_resistances)
        else:
            resist_text = "无"
        
        # 绘制抗性内容 - 调整位置与大边框对齐
        self.canvas.drawString(resist_text, 160 + header_width + 10, table_y + 16, font, text_paint)
    
    def _calculate_optimal_widths(self, row_data, available_width):
        """根据内容长度智能分配列宽，确保总宽度一致"""
        if not row_data:
            return []
        
        # 计算每列内容的最小宽度需求
        min_widths = []
        for name, value in row_data:
            name_len = len(str(name))
            value_len = len(str(value))
            # 估算最小宽度：较长文本需要更多空间
            min_width = max(name_len, value_len) * 7 + 8  # 7px每字符+边距
            min_widths.append(min_width)
        
        # 确保总宽度等于available_width
        total_min_width = sum(min_widths)
        if total_min_width > available_width:
            # 按比例缩放，确保总宽度不超过available_width
            scale = available_width / total_min_width
            scaled_widths = [int(w * scale) for w in min_widths]
            # 处理舍入误差，确保总宽度准确
            diff = available_width - sum(scaled_widths)
            if diff > 0:
                scaled_widths[-1] += diff  # 将剩余像素分给最后一列
            return scaled_widths
        else:
            # 平均分配剩余空间，确保总宽度等于available_width
            extra_space = available_width - total_min_width
            extra_per_col = extra_space // len(row_data)
            remainder = extra_space % len(row_data)
            
            final_widths = []
            for i, w in enumerate(min_widths):
                width = w + extra_per_col
                if i < remainder:  # 将余数分给前几列
                    width += 1
                final_widths.append(width)
            return final_widths

    def _draw_abnormal_resistances(self, enemy: EnemyData):
        """绘制异常抗性专区 - 简洁单行显示8种状态"""
        # 异常抗性区域背景 - 调整位置适应新表格高度
        resist_rect = skia.Rect(160, 142, 630, 162)  # 适应26*3+4的表格高度
        
        # 背景 - 使用标准矩形圆角避免锯齿
        bg_paint = skia.Paint(Color=skia.Color4f(0.95, 0.95, 0.95, 0.95), AntiAlias=True)
        self.canvas.drawRoundRect(resist_rect, 2, 2, bg_paint)  # 减小圆角半径
        
        # 边框
        border_paint = skia.Paint(Color=skia.Color4f(0.7, 0.7, 0.7, 0.8), AntiAlias=True)
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(1)
        self.canvas.drawRoundRect(resist_rect, 2, 2, border_paint)  # 减小圆角半径
        
        # 标题和抗性内容 - 单行显示
        font = self.font_manager.get_font(9)
        title_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)
        text_paint = skia.Paint(Color=skia.Color4f(0.3, 0.3, 0.3, 1), AntiAlias=True)
        
        # 根据abnormal_resistances动态显示抗性
        active_resistances = []
        for resistance_name, value in enemy.abnormal_resistances.items():
            if value == 1:  # 只显示值为1的抗性
                active_resistances.append(resistance_name)
        
        if active_resistances:
            resist_text = " · ".join(active_resistances)
        else:
            resist_text = "没有任何抗性"
        
        # 绘制标题和内容在同一行
        self.canvas.drawString("异常抗性", 165, 155, font, title_paint)
        self.canvas.drawString(resist_text, 235, 155, font, text_paint)
    
    def _draw_rating_cards(self, enemy: EnemyData):
        """绘制评价卡片系统 - 左侧垂直排列，移除分数显示"""
        ratings = [
            ("对策度", enemy.hostility_rating, (0.85, 0.2, 0.3)),
            ("创新度", enemy.innovation_rating, (0.2, 0.6, 0.9)), 
            ("威胁度", enemy.threat_rating, (0.9, 0.5, 0.1))
        ]
        
        # 评价区域整体布局 - 左侧垂直排列
        start_x = 20  # 移到最左侧
        start_y = 180
        card_width = 120
        card_height = 35  # 减小高度
        spacing = 42  # 减小卡片间距
        
        for i, (name, rating, color) in enumerate(ratings):
            x = start_x
            y = start_y + i * spacing  # 垂直排列
            
            # 卡片主体 - 渐变背景
            card_rect = skia.Rect(x, y, x + card_width, y + card_height)
            gradient_colors = [
                skia.Color4f(*color, 0.85),
                skia.Color4f(color[0] * 0.8, color[1] * 0.8, color[2] * 0.8, 0.85)
            ]
            gradient = skia.GradientShader.MakeLinear(
                points=[(x, y), (x, y + card_height)],
                colors=gradient_colors
            )
            card_paint = skia.Paint(Shader=gradient)
            self.canvas.drawRoundRect(card_rect, 6, 6, card_paint)
            
            # 卡片边框
            border_paint = skia.Paint(Color=skia.Color4f(*color, 0.9))
            border_paint.setStyle(skia.Paint.kStroke_Style)
            border_paint.setStrokeWidth(1.5)
            self.canvas.drawRoundRect(card_rect, 6, 6, border_paint)
            
            # 评价名称（左侧显示）
            name_font = self.font_manager.get_font(11)
            name_font.setEmbolden(True)
            name_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 1), AntiAlias=True)
            self.canvas.drawString(name, x + 8, y + 22, name_font, name_paint)
            
            # 星级显示 - 在名称右侧，更紧凑
            name_width = name_font.measureText(name)
            star_start_x = x + 15 + name_width
            star_size = 5  # 稍微减小星级大小
            for j in range(5):
                star_x = star_start_x + j * 11
                star_y = y + 18
                
                if j < rating:
                    # 实心星星 - 金色
                    self._draw_premium_star(star_x, star_y, star_size, (1.0, 0.9, 0.3))
                else:
                    # 空心星星
                    self._draw_empty_star(star_x, star_y, star_size)
    
    def _split_text(self, text: str, max_chars: int) -> list[str]:
        """将长文本分割成多行"""
        if len(text) <= max_chars:
            return [text]
        
        lines = []
        while text:
            if len(text) <= max_chars:
                lines.append(text)
                break
            # 在合适位置分割
            split_pos = max_chars
            while split_pos > 0 and text[split_pos] not in '，。！？；':
                split_pos -= 1
            if split_pos == 0:
                split_pos = max_chars
            
            lines.append(text[:split_pos])
            text = text[split_pos:].lstrip('，。！？；')
        
        return lines
    
    def _wrap_text(self, text: str, max_width: int, font_size: int) -> list[str]:
        """智能文本换行，根据像素宽度分割文本"""
        if not text:
            return [""]
        
        font = self.font_manager.get_font(font_size)
        words = []
        current_word = ""
        
        # 将文本分割为单词和标点符号
        for char in text:
            if char in "，。！？；、":
                current_word += char
                words.append(current_word)
                current_word = ""
            elif char == " ":
                if current_word:
                    words.append(current_word)
                    current_word = ""
                words.append(" ")
            else:
                current_word += char
        
        if current_word:
            words.append(current_word)
        
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + word
            test_width = font.measureText(test_line)
            
            if test_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                    current_line = word
                else:
                    # 单词本身就超过最大宽度，强制分割
                    lines.append(word[:20] + "...")
                    current_line = ""
        
        if current_line:
            lines.append(current_line.strip())
        
        return lines if lines else [""]
    
    def _draw_shield_icon(self, cx: float, cy: float, radius: float):
        """绘制盾牌形状图标"""
        import math
        
        # 创建盾牌形状路径
        path = skia.Path()
        
        # 盾牌上部分（半圆）
        top_rect = skia.Rect(cx - radius, cy - radius, cx + radius, cy)
        path.addArc(top_rect, 180, 180)
        
        # 盾牌下部分（三角形尖端）
        path.lineTo(cx + radius * 0.7, cy)
        path.lineTo(cx, cy + radius * 0.8)
        path.lineTo(cx - radius * 0.7, cy)
        path.close()
        
        # 填充盾牌
        shield_paint = skia.Paint(Color=skia.Color4f(0.3, 0.3, 0.3, 1), AntiAlias=True)
        self.canvas.drawPath(path, shield_paint)
        
        # 盾牌边框
        border_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(0.5)
        self.canvas.drawPath(path, border_paint)

    def _draw_filled_star(self, cx: float, cy: float, radius: float):
        """绘制实心五角星"""
        import math
        
        path = skia.Path()
        outer_radius = radius
        inner_radius = radius * 0.4
        
        path.moveTo(cx, cy - outer_radius)
        
        for i in range(1, 11):
            angle = i * math.pi / 5
            if i % 2 == 1:
                r = inner_radius
            else:
                r = outer_radius
            
            x = cx + r * math.sin(angle)
            y = cy - r * math.cos(angle)
            path.lineTo(x, y)
        
        path.close()
        
        # 填充黑色
        paint = skia.Paint(Color=skia.Color4f(0, 0, 0, 1))
        self.canvas.drawPath(path, paint)
    
    def _draw_colored_star(self, cx: float, cy: float, radius: float, color: tuple):
        """绘制彩色实心五角星"""
        import math
        
        path = skia.Path()
        outer_radius = radius
        inner_radius = radius * 0.4
        
        path.moveTo(cx, cy - outer_radius)
        
        for i in range(1, 11):
            angle = i * math.pi / 5
            if i % 2 == 1:
                r = inner_radius
            else:
                r = outer_radius
            
            x = cx + r * math.sin(angle)
            y = cy - r * math.cos(angle)
            path.lineTo(x, y)
        
        path.close()
        
        # 填充指定颜色
        paint = skia.Paint(Color=skia.Color4f(*color, 1))
        self.canvas.drawPath(path, paint)
    
    def _draw_premium_star(self, cx: float, cy: float, radius: float, color: tuple):
        """绘制精美的实心五角星"""
        import math
        
        path = skia.Path()
        outer_radius = radius
        inner_radius = radius * 0.4
        
        path.moveTo(cx, cy - outer_radius)
        
        for i in range(1, 11):
            angle = i * math.pi / 5
            if i % 2 == 1:
                r = inner_radius
            else:
                r = outer_radius
            
            x = cx + r * math.sin(angle)
            y = cy - r * math.cos(angle)
            path.lineTo(x, y)
        
        path.close()
        
        # 星星渐变效果
        gradient_colors = [
            skia.Color4f(*color, 1.0),
            skia.Color4f(color[0] * 0.8, color[1] * 0.8, color[2] * 0.8, 1.0)
        ]
        gradient = skia.GradientShader.MakeRadial(
            center=(cx, cy),
            radius=outer_radius,
            colors=gradient_colors
        )
        paint = skia.Paint(Shader=gradient)
        self.canvas.drawPath(path, paint)
        
        # 添加边框增强立体感
        border_paint = skia.Paint(Color=skia.Color4f(color[0] * 0.6, color[1] * 0.6, color[2] * 0.6, 0.8))
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(0.5)
        self.canvas.drawPath(path, border_paint)

    def _draw_empty_star(self, cx: float, cy: float, radius: float):
        """绘制空心五角星"""
        import math
        
        path = skia.Path()
        outer_radius = radius
        inner_radius = radius * 0.4
        
        path.moveTo(cx, cy - outer_radius)
        
        for i in range(1, 11):
            angle = i * math.pi / 5
            if i % 2 == 1:
                r = inner_radius
            else:
                r = outer_radius
            
            x = cx + r * math.sin(angle)
            y = cy - r * math.cos(angle)
            path.lineTo(x, y)
        
        path.close()
        
        # 只绘制边框
        paint = skia.Paint(Color=skia.Color4f(0.7, 0.7, 0.7, 1))
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(1)
        self.canvas.drawPath(path, paint)
    
    def _draw_grade_section(self, enemy: EnemyData):
        """绘制综合评级框 - 左下角位置"""
        # 等级卡片背景 - 移到左下角
        grade_rect = skia.Rect(20, 350, 140, 420)
        grade_color = self.grade_colors.get(enemy.grade, (0.6, 0.6, 0.6, 1.0))
        
        # 渐变背景
        gradient_colors = [
            skia.Color4f(*grade_color),
            skia.Color4f(grade_color[0] * 0.7, grade_color[1] * 0.7, grade_color[2] * 0.7, grade_color[3])
        ]
        gradient = skia.GradientShader.MakeLinear(
            points=[(20, 350), (140, 420)],
            colors=gradient_colors
        )
        grade_paint = skia.Paint(Shader=gradient)
        self.canvas.drawRoundRect(grade_rect, 8, 8, grade_paint)
        
        # 边框
        border_paint = skia.Paint(Color=skia.Color4f(*grade_color))
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(1.5)
        self.canvas.drawRoundRect(grade_rect, 8, 8, border_paint)
        
        # 等级字母 - 居中显示
        grade_font = self.font_manager.get_font(42)
        grade_font.setEmbolden(True)
        text_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 1), AntiAlias=True)
        
        # 文字阴影
        shadow_paint = skia.Paint(Color=skia.Color4f(0, 0, 0, 0.3), AntiAlias=True)
        grade_width = grade_font.measureText(enemy.grade)
        grade_x = 80 - grade_width / 2
        self.canvas.drawString(enemy.grade, grade_x + 2, 397, grade_font, shadow_paint)
        self.canvas.drawString(enemy.grade, grade_x, 395, grade_font, text_paint)
        
        # 简评区域 - 紧挨着评级右侧
        comment_rect = skia.Rect(160, 350, 620, 420)
        
        # 简评背景
        comment_paint = skia.Paint(Color=skia.Color4f(0.96, 0.96, 0.96, 0.9))
        self.canvas.drawRoundRect(comment_rect, 6, 6, comment_paint)
        
        # 简评边框
        comment_border = skia.Paint(Color=skia.Color4f(0.75, 0.75, 0.75, 0.8))
        comment_border.setStyle(skia.Paint.kStroke_Style)
        comment_border.setStrokeWidth(1)
        self.canvas.drawRoundRect(comment_rect, 6, 6, comment_border)
        
        # 简评文字 - 使用手填的简评内容
        comment_font = self.font_manager.get_font(11)
        comment_text_paint = skia.Paint(Color=skia.Color4f(0.4, 0.4, 0.4, 1), AntiAlias=True)
        
        # 分行显示简评内容
        lines = self._split_text(enemy.brief_comment, 40)
        max_lines = 3  # 最多显示3行
        for i, line in enumerate(lines[:max_lines]):
            y_pos = 375 + i * 15
            if i == 0:
                line = f"简评：{line}"
            else:
                line = f"      {line}"  # 缩进对齐
            self.canvas.drawString(line, 170, y_pos, comment_font, comment_text_paint)
    
    
    def generate_card(self, enemy: EnemyData, output_path: Optional[str] = None) -> str:
        """生成敌人评价卡片"""
        # 初始化画布
        self._init_canvas()
        
        # 绘制各个部分 - 使用统一信息框
        self._draw_avatar_section(enemy)
        self._draw_unified_info_section(enemy)  # 替换原来的三个独立方法
        self._draw_rating_cards(enemy)
        self._draw_grade_section(enemy)
        
        # 保存图片
        if not output_path:
            output_path = f"output_{enemy.name}_{enemy.grade}.png"
            
        image = self.surface.makeImageSnapshot()
        image.save(output_path, skia.kPNG)
        
        return output_path