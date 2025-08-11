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
        self.height = 450
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
        
        # 绘制方形头像
        if enemy.avatar_path and Path(enemy.avatar_path).exists():
            try:
                pil_img = Image.open(enemy.avatar_path)
                pil_img = pil_img.resize((110, 110))
                
                if pil_img.mode != 'RGBA':
                    pil_img = pil_img.convert('RGBA')
                    
                img_array = np.array(pil_img)
                skia_img = skia.Image.fromarray(img_array)
                
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
        # 表格背景 - 调整位置适应描述区域
        table_rect = skia.Rect(160, 55, 630, 120)
        
        # 主背景
        paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 0.98))
        self.canvas.drawRoundRect(table_rect, 6, 6, paint)
        
        # 表格边框
        border_paint = skia.Paint(Color=skia.Color4f(0.7, 0.7, 0.7, 1))
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(1)
        self.canvas.drawRoundRect(table_rect, 6, 6, border_paint)
        
        # 字体设置
        font_name = self.font_manager.get_font(9)
        font_value = self.font_manager.get_font(11)
        name_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)
        value_paint = skia.Paint(Color=skia.Color4f(0, 0, 0, 1), AntiAlias=True)
        
        # 表格数据（2行6列紧凑布局）
        attrs_data = [
            [("最大生命值", enemy.max_hp), ("攻击力", enemy.attack), ("防御力", enemy.defense), ("法术抗性", enemy.magic_resistance), ("攻击间隔", enemy.attack_interval), ("攻击范围", enemy.attack_range_radius)],
            [("目标价值", enemy.target_value), ("移动速度", enemy.move_speed), ("重量等级", enemy.weight_level), ("元素抗性", enemy.element_resistance), ("损伤抗性", enemy.damage_resistance), ("生命恢复速度", enemy.hp_recovery_speed)]
        ]
        
        # 表格参数 - 调整位置
        start_x = 165
        start_y = 60
        cell_width = 75
        cell_height = 26
        
        # 网格和背景paint
        grid_paint = skia.Paint(Color=skia.Color4f(0.8, 0.8, 0.8, 1))
        grid_paint.setStyle(skia.Paint.kStroke_Style)
        grid_paint.setStrokeWidth(1)
        
        # 列名背景色
        header_bg_paint = skia.Paint(Color=skia.Color4f(0.95, 0.95, 0.97, 1))
        
        # 绘制表格内容
        for row_idx, row_data in enumerate(attrs_data):
            y = start_y + row_idx * cell_height
            
            for col_idx, (name, value) in enumerate(row_data):
                x = start_x + col_idx * cell_width
                cell_rect = skia.Rect(x, y, x + cell_width, y + cell_height)
                
                # 绘制列名区域背景（上半部分）
                header_rect = skia.Rect(x, y, x + cell_width, y + cell_height // 2)
                self.canvas.drawRect(header_rect, header_bg_paint)
                
                # 绘制单元格边框
                self.canvas.drawRect(cell_rect, grid_paint)
                
                # 绘制属性名（上方，居中对齐）
                name_width = font_name.measureText(name)
                name_x = x + (cell_width - name_width) / 2
                self.canvas.drawString(name, name_x, y + 10, font_name, name_paint)
                
                # 绘制属性值（下方，居中对齐）
                value_str = str(value) if isinstance(value, (int, str)) else f"{value:.1f}"
                value_width = font_value.measureText(value_str)
                value_x = x + (cell_width - value_width) / 2
                self.canvas.drawString(value_str, value_x, y + 22, font_value, value_paint)
    
    def _draw_brief_description(self, enemy: EnemyData):
        """绘制简要描述（支持多行显示）"""
        # 描述区域背景 - 调整高度支持多行
        desc_rect = skia.Rect(160, 20, 630, 50)
        
        # 背景
        desc_paint = skia.Paint(Color=skia.Color4f(0.98, 0.98, 0.98, 0.9))
        self.canvas.drawRoundRect(desc_rect, 4, 4, desc_paint)
        
        # 边框
        border_paint = skia.Paint(Color=skia.Color4f(0.85, 0.85, 0.85, 0.8))
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(0.5)
        self.canvas.drawRoundRect(desc_rect, 4, 4, border_paint)
        
        # 描述内容支持多行显示
        desc_font = self.font_manager.get_font(10)
        content_paint = skia.Paint(Color=skia.Color4f(0.3, 0.3, 0.3, 1), AntiAlias=True)
        
        # 分行显示描述内容
        lines = self._split_text(enemy.brief_description, 50)  # 每行约50字符，适应框宽
        max_lines = 2  # 最多显示2行
        for i, line in enumerate(lines[:max_lines]):
            y_pos = 32 + i * 12  # 行间距12px
            if i == max_lines - 1 and len(lines) > max_lines:
                line = line[:47] + "..."  # 最后一行如果过长则截断
            self.canvas.drawString(line, 165, y_pos, desc_font, content_paint)
    
    def _draw_abnormal_resistances(self, enemy: EnemyData):
        """绘制异常抗性专区 - 调整位置并显示完整描述"""
        # 过滤出有抗性的项目（值 > 0）
        active_resistances = {k: v for k, v in enemy.abnormal_resistances.items() if v > 0}
        
        # 异常抗性区域背景 - 调整位置
        resist_rect = skia.Rect(160, 130, 630, 165)
        
        # 背景
        bg_paint = skia.Paint(Color=skia.Color4f(0.95, 0.98, 0.95, 0.95))
        self.canvas.drawRoundRect(resist_rect, 6, 6, bg_paint)
        
        # 边框
        border_paint = skia.Paint(Color=skia.Color4f(0.2, 0.8, 0.5, 0.8))
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(1)
        self.canvas.drawRoundRect(resist_rect, 6, 6, border_paint)
        
        # 标题
        title_font = self.font_manager.get_font(10)
        title_paint = skia.Paint(Color=skia.Color4f(0.2, 0.6, 0.3, 1), AntiAlias=True)
        self.canvas.drawString("异常抗性", 165, 145, title_font, title_paint)
        
        # 完整抗性描述显示
        font = self.font_manager.get_font(9)
        text_paint = skia.Paint(Color=skia.Color4f(0.3, 0.3, 0.3, 1), AntiAlias=True)
        
        if not active_resistances:
            self.canvas.drawString("无异常抗性", 250, 150, font, text_paint)
        else:
            # 显示抗性名称，不重复添加"抗性"字样
            resist_text = "  ".join(active_resistances.keys())
            # 限制显示长度以适应框大小
            if len(resist_text) > 50:
                resist_text = resist_text[:47] + "..."
            self.canvas.drawString(resist_text, 250, 150, font, text_paint)
    
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
        
        # 绘制各个部分 - 使用更新的方法名
        self._draw_avatar_section(enemy)
        self._draw_main_stats_table(enemy) 
        self._draw_brief_description(enemy)
        self._draw_abnormal_resistances(enemy)
        self._draw_rating_cards(enemy)
        self._draw_grade_section(enemy)
        
        # 保存图片
        if not output_path:
            output_path = f"output_{enemy.name}_{enemy.grade}.png"
            
        image = self.surface.makeImageSnapshot()
        image.save(output_path, skia.kPNG)
        
        return output_path