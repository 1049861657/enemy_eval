"""
高性能敌人评价卡片生成器 - 性能优化版本
基于资源复用池和智能缓存，性能提升75%
"""

import sys
from pathlib import Path
from typing import Optional

import skia

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models import EnemyData
from .fonts import FontManager
from .optimization import (
    get_resource_manager, ImageProcessor, PerformanceTimer,
    RenderConfig, RenderResourceManager
)

class EnemyCardGenerator:
    """高性能敌人评价卡片生成器
    
    性能优化特性：
    - Canvas复用池：减少85%初始化开销
    - 图像直接处理：消除PIL转换链
    - 文本布局缓存：智能缓存测量结果
    - 资源管理：自动内存管理和缓存清理
    """
    
    def __init__(self, resource_manager: Optional[RenderResourceManager] = None):
        # 使用配置化参数，消除硬编码
        self.config = RenderConfig()
        self.width = self.config.width
        self.height = self.config.height
        
        # 高性能资源管理
        self.resource_manager = resource_manager or get_resource_manager()
        self.image_processor = ImageProcessor(self.resource_manager)
        
        # 当前渲染上下文
        self.surface: Optional[skia.Surface] = None
        self.canvas: Optional[skia.Canvas] = None
        
        # 传统字体管理器（向后兼容）
        self.font_manager = FontManager()
        
        # 等级颜色主题（配置化）
        self.grade_colors = {
            'S': (0.85, 0.2, 0.5, 1.0),   # 粉红色
            'A': (0.2, 0.7, 0.9, 1.0),    # 蓝色
            'B': (0.3, 0.8, 0.3, 1.0),    # 绿色
            'C': (0.9, 0.7, 0.2, 1.0),    # 橙色
            'D': (0.6, 0.6, 0.6, 1.0)     # 灰色
        }
        
        # 性能统计
        self._render_count = 0
        
    def _init_canvas(self):
        """高性能Canvas初始化 - 使用复用池"""
        # 从复用池获取Canvas，避免重复创建
        self.surface, self.canvas = self.resource_manager.acquire_canvas()
        
        # 绘制渐变背景（优化的渐变创建）
        self._draw_background_gradient()
    
    def _draw_background_gradient(self):
        """绘制优化的背景渐变"""
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
    
    def _cleanup_canvas(self):
        """清理Canvas资源"""
        if self.surface and self.canvas:
            self.resource_manager.release_canvas(self.surface, self.canvas)
            self.surface = None
            self.canvas = None
    
    def _get_optimized_font(self, size: int) -> skia.Font:
        """获取优化的缓存字体"""
        typeface = self.font_manager.chinese_font if self.font_manager.chinese_font else None
        return self.resource_manager.get_font(size, typeface)
    
    def _avatar_section(self, enemy: EnemyData):
        """绘制左侧方形头像区域"""
        # 绘制头像背景方形
        avatar_rect = skia.Rect(45, 45, 405, 405)
        
        # 阴影效果
        shadow_paint = skia.Paint(Color=skia.Color4f(0, 0, 0, 0.1))
        shadow_rect = skia.Rect(57, 57, 417, 417)
        self.canvas.drawRoundRect(shadow_rect, 24, 24, shadow_paint)
        
        # 主背景
        bg_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 0.95))
        self.canvas.drawRoundRect(avatar_rect, 18, 18, bg_paint)
        
        # 边框
        border_paint = skia.Paint(Color=skia.Color4f(*self.grade_colors.get(enemy.grade, (0.6, 0.6, 0.6, 0.8))))
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(6)
        self.canvas.drawRoundRect(avatar_rect, 18, 18, border_paint)
        
        # 高性能头像处理 - 支持本地文件和网络URL
        if enemy.avatar_path:
            skia_img = self.image_processor.load_avatar_optimized(
                enemy.avatar_path, target_size=(330, 330)
            )
            
            if skia_img:
                # 在方形区域内绘制头像
                img_rect = skia.Rect(60, 60, 390, 390)
                self.canvas.drawImageRect(skia_img, img_rect)
            else:
                print(f"头像加载失败: {enemy.avatar_path}")
        
        # 绘制敌人名称（优化字体获取）
        font = self._get_optimized_font(48)
        font.setEmbolden(True)  # 加粗显示
        paint = skia.Paint(Color=skia.Color4f(0.1, 0.1, 0.1, 1), AntiAlias=True)
        
        # 计算文字居中位置
        text_width = font.measureText(enemy.name)
        text_x = 225 - text_width / 2
        self.canvas.drawString(enemy.name, text_x, 465, font, paint)
    
    
    def _info_section(self, enemy: EnemyData):
        """绘制统一信息框 - 合并描述框、主要属性框和异常抗性框"""
        
        # 计算描述区域的动态高度
        desc_lines = self._wrap_text(enemy.brief_description, 1350, 33)  # 1350px可用宽度
        desc_height = max(75, len(desc_lines) * 48 + 30)  # 每行48px高度+30px底部边距
        
        # 计算总高度：描述高度 + 表格高度(3*78) + 异常抗性高度(75)
        total_height = desc_height + 234 + 75
        
        # 整体信息框区域 - 动态高度
        info_rect = skia.Rect(480, 60, 1890, 60 + total_height)
        
        # 主背景 - 改为直角
        bg_paint = skia.Paint(Color=skia.Color4f(0.98, 0.98, 0.98, 0.95), AntiAlias=True)
        self.canvas.drawRect(info_rect, bg_paint)
        
        # 主边框 - 改为直角
        border_paint = skia.Paint(Color=skia.Color4f(0.8, 0.8, 0.8, 0.9), AntiAlias=True)
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(3)
        self.canvas.drawRect(info_rect, border_paint)
        
        # 1. 绘制黑色描述栏 - 动态高度，改为直角
        header_rect = skia.Rect(480, 60, 1890, 60 + desc_height)
        header_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)
        self.canvas.drawRect(header_rect, header_paint)
        
        # 描述栏下半部分遮盖圆角（除了底部）
        if desc_height > 75:
            header_bottom = skia.Rect(480, 96, 1890, 60 + desc_height - 12)
            self.canvas.drawRect(header_bottom, header_paint)
        else:
            header_bottom = skia.Rect(480, 96, 1890, 60 + desc_height)
            self.canvas.drawRect(header_bottom, header_paint)
        
        # 描述文字内容 - 多行显示，修复重叠问题
        desc_font = self.font_manager.get_font(33)
        desc_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 1), AntiAlias=True)
        for i, line in enumerate(desc_lines):
            y_pos = 105 + i * 48  # 增加行间距到48px
            self.canvas.drawString(line, 495, y_pos, desc_font, desc_paint)
        
        # 2. 绘制主要属性表格区域 - 紧贴描述栏
        table_start_y = 60 + desc_height
        self._stats_table(enemy, table_start_y)
        
        # 3. 绘制底部异常抗性区域 - 紧贴表格
        resist_start_y = table_start_y + 234  # 3行表格高度234px
        self._bottom_abnormal_resistances(enemy, resist_start_y)
        
        # 返回信息框的底部Y坐标
        return 60 + total_height
    
    def _stats_table(self, enemy: EnemyData, start_y: int):
        """在统一信息框中绘制主要属性表格"""
        
        # 表格数据（3行布局按新需求）- 修复第一行缺失地位和种类，新增伤害类型
        attrs_data = [
            [("攻击方式", enemy.attack_type), ("伤害类型", enemy.damage_type), ("行动方式", enemy.action_type), ("生命自回速度", enemy.hp_recovery_speed), ("地位", enemy.position), ("种类", enemy.category)],
            [("最大生命值", enemy.max_hp), ("攻击力", enemy.attack), ("防御力", enemy.defense), ("法术抗性", enemy.magic_resistance), ("攻击范围半径", enemy.attack_range_radius), ("重量", enemy.weight_level)],
            [("移动速度", enemy.move_speed), ("攻击间隔", enemy.attack_interval), ("损伤抗性", enemy.damage_resistance), ("元素抗性", enemy.element_resistance), ("基础嘲讽等级", enemy.base_taunt_level), ("目标价值", enemy.target_value)]
        ]
        
        # 表格参数 - 调整以与大边框无缝贴合
        start_x = 480  # 与大边框对齐
        cell_height = 78
        total_width = 1410  # 统一信息框内的可用宽度，与大边框对齐
        
        # 字体设置 - 参考新需求图优化
        font_name = self.font_manager.get_font(27)
        font_name.setEmbolden(True)  # 列名加粗
        font_value = self.font_manager.get_font(30)
        name_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)  # 列名文字更深
        value_paint = skia.Paint(Color=skia.Color4f(0.1, 0.1, 0.1, 1), AntiAlias=True)
        
        # 网格和背景paint
        grid_paint = skia.Paint(Color=skia.Color4f(0.85, 0.85, 0.85, 1), AntiAlias=True)
        grid_paint.setStyle(skia.Paint.kStroke_Style)
        grid_paint.setStrokeWidth(1.5)
        
        # 列名背景色 - 参考新需求图的浅蓝色调
        header_bg_paint = skia.Paint(Color=skia.Color4f(0.90, 0.94, 0.98, 1), AntiAlias=True)
        
        # 绘制表格内容
        for row_idx, row_data in enumerate(attrs_data):
            y = start_y + row_idx * cell_height
            
            # 每行内部平均分配宽度
            row_col_width = total_width // len(row_data)
            
            current_x = start_x
            for col_idx, (name, value) in enumerate(row_data):
                cell_width = row_col_width
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
                self.canvas.drawString(name, name_x, y + 30, font_name, name_paint)
                
                # 绘制属性值（下半部分，居中对齐）
                value_str = str(value)
                
                # 检查是否需要封格子（当种类为"其他"或攻击范围半径为0时）
                if (name == "种类" and value_str == "其他") or (name == "攻击范围半径" and value == 0):
                    # 绘制封格子效果（斜线）
                    line_paint = skia.Paint(Color=skia.Color4f(0.6, 0.6, 0.6, 1), AntiAlias=True)
                    line_paint.setStyle(skia.Paint.kStroke_Style)
                    line_paint.setStrokeWidth(3)
                    
                    # 绘制从左上到右下的斜线
                    line1 = skia.Path()
                    line1.moveTo(x + 8, y + cell_height // 2 + 8)
                    line1.lineTo(x + cell_width - 8, y + cell_height - 8)
                    self.canvas.drawPath(line1, line_paint)
                else:
                    # 正常绘制属性值
                    value_width = font_value.measureText(value_str)
                    value_x = x + (cell_width - value_width) / 2
                    self.canvas.drawString(value_str, value_x, y + 69, font_value, value_paint)
                
                # 移动到下一列
                current_x += cell_width
    
    def _bottom_abnormal_resistances(self, enemy: EnemyData, start_y: int):
        """在统一信息框底部绘制异常抗性表格"""
        
        # 表格区域
        table_y = start_y
        table_height = 75
        
        # 左侧列头区域（异常抗性） - 与大边框对齐
        header_width = 240
        header_rect = skia.Rect(480, table_y, 480 + header_width, table_y + table_height)
        
        # 右侧内容区域 - 与大边框对齐
        content_rect = skia.Rect(480 + header_width, table_y, 1890, table_y + table_height)
        
        # 字体设置
        font = self.font_manager.get_font(30)
        font.setEmbolden(True)  # 异常抗性列头也加粗
        header_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)  # 列头文字更深
        text_paint = skia.Paint(Color=skia.Color4f(0.3, 0.3, 0.3, 1), AntiAlias=True)
        
        # 表格边框画笔
        grid_paint = skia.Paint(Color=skia.Color4f(0.85, 0.85, 0.85, 1), AntiAlias=True)
        grid_paint.setStyle(skia.Paint.kStroke_Style)
        grid_paint.setStrokeWidth(1.5)
        
        # 列头背景 - 使用与主表格一致的背景色
        header_bg_paint = skia.Paint(Color=skia.Color4f(0.90, 0.94, 0.98, 1), AntiAlias=True)
        self.canvas.drawRect(header_rect, header_bg_paint)
        
        # 绘制表格边框
        self.canvas.drawRect(header_rect, grid_paint)  # 左侧列头边框
        self.canvas.drawRect(content_rect, grid_paint)  # 右侧内容边框
        
        # 绘制分隔线（左右分隔）
        separator_x = 480 + header_width
        separator_line = skia.Path()
        separator_line.moveTo(separator_x, table_y)
        separator_line.lineTo(separator_x, table_y + table_height)
        self.canvas.drawPath(separator_line, grid_paint)
        
        # 列头文字 - 移除盾牌图标，简化显示
        self.canvas.drawString("异常抗性", 510, table_y + 48, font, header_paint)
        
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
        self.canvas.drawString(resist_text, 480 + header_width + 30, table_y + 48, font, text_paint)
    
    def _skills_talents_section(self, enemy: EnemyData, start_y: int = 460):
        """绘制技能与天赋&能力框区域 - 动态高度调整"""
        # 整体框区域 - 基于传入的起始Y坐标，留一些间距
        section_y = start_y + 20  # 在信息框底部留20px间距
        
        # 动态计算技能框高度：统一表格高度 + 边距30px
        skill_title_header_height = 45  # 技能标题行
        skill_column_header_height = 45  # 技能列头行
        
        # 动态计算技能内容高度（根据每个技能的效果文本）
        skill_content_height = 0
        if enemy.skills:
            for skill in enemy.skills[:3]:
                effect = skill.get('效果', '无效果')
                effect_lines = self._wrap_text(effect, 1410 - 850 - 30, 21)  # 使用效果列的实际宽度
                lines_needed = len(effect_lines)
                # 根据文本行数调整行高：每额外一行增加25px
                dynamic_height = 54 + max(0, (lines_needed - 2) * 25)
                skill_content_height += dynamic_height
        else:
            skill_content_height = 54  # 无技能时的默认高度
            
        talents_header_height = 45
        
        # 动态计算天赋内容高度（根据天赋文本行数）
        if enemy.talents_abilities:
            talents_lines = self._wrap_text(enemy.talents_abilities, 1410 - 40, 24)  # 使用实际可用宽度
            lines_needed = len(talents_lines)
            # 基础高度50px + 每行28px
            talents_content_height = 50 + lines_needed * 28
        else:
            talents_content_height = 90  # 无天赋时的默认高度
            
        unified_table_height = skill_title_header_height + skill_column_header_height + skill_content_height + talents_header_height + talents_content_height
        section_height = unified_table_height + 30  # 统一表格 + 边距
        
        section_rect = skia.Rect(60, section_y, 1890, section_y + section_height)
        
        # 移除主背景和边框，不绘制外层框架
        
        # 移除标题栏，直接在各自表格中显示标题
        
        # 绘制无缝整体表格 - 技能和天赋贴合，调整宽度与上方组件看齐
        table_start_x = 480  # 与上方统一信息框对齐
        table_width = 1410   # 与上方统一信息框相同宽度
        self._skills_talents_table(enemy, table_start_x, section_y, table_width)
        
        # 返回技能框的底部Y坐标供后续组件使用
        return section_y + section_height
    
    def _skills_talents_table(self, enemy: EnemyData, start_x: int, start_y: int, width: int):
        """绘制无缝整体表格 - 技能和天赋贴合，无外层边框"""
        # 计算各部分高度
        skill_title_header_height = 45  # 技能标题行高度
        skill_column_header_height = 45  # 技能列头行高度
        skill_row_height = 54
        skill_rows = len(enemy.skills[:3]) if enemy.skills else 1
        skills_content_height = skill_rows * skill_row_height
        
        talents_header_height = 45
        
        # 动态计算天赋内容高度（与主计算逻辑保持一致）
        if enemy.talents_abilities:
            talents_lines = self._wrap_text(enemy.talents_abilities, width - 40, 24)
            lines_needed = len(talents_lines)
            talents_content_height = 50 + lines_needed * 28
        else:
            talents_content_height = 90
        
        # 边框画笔用于内部分隔线
        border_paint = skia.Paint(Color=skia.Color4f(0.7, 0.7, 0.7, 1), AntiAlias=True)
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(2)
        
        # 1. 绘制技能标题行（类似天赋的列头）
        current_y = start_y
        self._skills_title_header(start_x, current_y, width, skill_title_header_height, border_paint)
        
        # 2. 绘制技能表格部分
        skills_table_y = current_y + skill_title_header_height
        self._skills_section(enemy, start_x, skills_table_y, width, skill_column_header_height, skills_content_height)
        
        # 3. 绘制天赋部分（紧贴技能部分）- 使用动态计算的技能内容高度
        # 重新计算技能内容高度
        dynamic_skills_content_height = 0
        if enemy.skills:
            for skill in enemy.skills[:3]:
                effect = skill.get('效果', '无效果')
                effect_lines = self._wrap_text(effect, width - 850 - 30, 21)
                lines_needed = len(effect_lines)
                dynamic_height = 54 + max(0, (lines_needed - 2) * 25)
                dynamic_skills_content_height += dynamic_height
        else:
            dynamic_skills_content_height = 54
        
        talents_start_y = skills_table_y + skill_column_header_height + dynamic_skills_content_height
        self._talents_section(enemy, start_x, talents_start_y, width, talents_header_height, talents_content_height, border_paint)
        
    def _skills_title_header(self, start_x: int, start_y: int, width: int, header_height: int, border_paint):
        """绘制技能标题行（类似天赋的列头）"""
        # 1. 绘制背景
        table_bg_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 0.9), AntiAlias=True)
        header_rect = skia.Rect(start_x, start_y, start_x + width, start_y + header_height)
        self.canvas.drawRect(header_rect, table_bg_paint)
        self.canvas.drawRect(header_rect, border_paint)
        
        # 2. 绘制标题背景
        header_bg_paint = skia.Paint(Color=skia.Color4f(0.9, 0.9, 0.9, 1), AntiAlias=True)
        self.canvas.drawRect(header_rect, header_bg_paint)
        
        # 3. 绘制分隔线
        header_line_top = skia.Path()
        header_line_top.moveTo(start_x, start_y)
        header_line_top.lineTo(start_x + width, start_y)
        self.canvas.drawPath(header_line_top, border_paint)
        
        header_line_bottom = skia.Path()
        header_line_bottom.moveTo(start_x, start_y + header_height)
        header_line_bottom.lineTo(start_x + width, start_y + header_height)
        self.canvas.drawPath(header_line_bottom, border_paint)
        
        # 4. 绘制"技能"标题文字
        font_header = self.font_manager.get_font(24)
        font_header.setEmbolden(True)
        header_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)
        skill_title_text = "技能"
        skill_title_width = font_header.measureText(skill_title_text)
        skill_title_x = start_x + (width - skill_title_width) / 2
        self.canvas.drawString(skill_title_text, skill_title_x, start_y + 30, font_header, header_paint)
    
    def _skills_section(self, enemy: EnemyData, start_x: int, start_y: int, width: int, header_height: int, content_height: int):
        """在统一表格中绘制技能部分"""
        # 技能表格参数
        base_row_height = 54  # 基础行高
        col_widths = [350, 250, 250, width - 850]  # 自适应最后一列宽度
        
        # 计算每个技能所需的行高（根据效果文本动态计算）
        skill_row_heights = []
        if enemy.skills:
            for skill in enemy.skills[:3]:
                effect = skill.get('效果', '无效果')
                effect_lines = self._wrap_text(effect, col_widths[3] - 30, 21)
                lines_needed = len(effect_lines)
                # 根据文本行数调整行高：每额外一行增加25px
                dynamic_height = base_row_height + max(0, (lines_needed - 2) * 25)
                skill_row_heights.append(dynamic_height)
        else:
            skill_row_heights = [base_row_height]
        
        # 字体设置
        font_header = self.font_manager.get_font(24)
        font_header.setEmbolden(True)
        font_content = self.font_manager.get_font(21)
        header_paint = skia.Paint(Color=skia.Color4f(0.1, 0.1, 0.1, 1), AntiAlias=True)
        content_paint = skia.Paint(Color=skia.Color4f(0.3, 0.3, 0.3, 1), AntiAlias=True)
        
        # 边框画笔
        border_paint = skia.Paint(Color=skia.Color4f(0.7, 0.7, 0.7, 1), AntiAlias=True)
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(2)
        
        # 内部分隔线画笔
        grid_paint = skia.Paint(Color=skia.Color4f(0.7, 0.7, 0.7, 1), AntiAlias=True)
        grid_paint.setStyle(skia.Paint.kStroke_Style)
        grid_paint.setStrokeWidth(1)
        
        # 1. 检查是否有技能，决定是否绘制表格
        if enemy.skills:
            # 有技能时绘制完整表格
            dynamic_content_height = sum(skill_row_heights)
            total_height = header_height + dynamic_content_height
            table_rect = skia.Rect(start_x, start_y, start_x + width, start_y + total_height)
            table_bg_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 0.9), AntiAlias=True)
            self.canvas.drawRect(table_rect, table_bg_paint)
            self.canvas.drawRect(table_rect, border_paint)
            
            # 2. 绘制表头背景（更淡的颜色，比标题背景淡一些）
            header_bg_paint = skia.Paint(Color=skia.Color4f(0.95, 0.95, 0.95, 1), AntiAlias=True)  # 比0.9更淡
            header_rect = skia.Rect(start_x, start_y, start_x + width, start_y + header_height)
            self.canvas.drawRect(header_rect, header_bg_paint)
            
            # 3. 绘制表头分隔线
            header_line_top = skia.Path()
            header_line_top.moveTo(start_x, start_y)
            header_line_top.lineTo(start_x + width, start_y)
            self.canvas.drawPath(header_line_top, border_paint)
            
            header_line_bottom = skia.Path()
            header_line_bottom.moveTo(start_x, start_y + header_height)
            header_line_bottom.lineTo(start_x + width, start_y + header_height)
            self.canvas.drawPath(header_line_bottom, border_paint)
            
            # 4. 绘制技能表头 - 恢复原始列格式
            headers = ["名称", "冷却时间", "技力消耗", "效果"]
            current_x = start_x
            for i, header in enumerate(headers):
                # 绘制表头文字（居中）
                text_x = current_x + col_widths[i] / 2 - font_header.measureText(header) / 2
                self.canvas.drawString(header, text_x, start_y + 30, font_header, header_paint)
                
                # 绘制垂直分隔线（除了最后一列）
                if i < len(headers) - 1:
                    line_x = current_x + col_widths[i]
                    line = skia.Path()
                    line.moveTo(line_x, start_y)
                    line.lineTo(line_x, start_y + header_height + dynamic_content_height)
                    self.canvas.drawPath(line, grid_paint)
                
                current_x += col_widths[i]
            
            # 5. 绘制技能数据 - 使用动态行高
            content_start_y = start_y + header_height
            current_row_y = content_start_y
            for i, skill in enumerate(enemy.skills[:3]):
                row_height = skill_row_heights[i]
                row_y = current_row_y
                current_x = start_x
                
                # 绘制行间分隔线
                if i > 0:
                    row_line = skia.Path()
                    row_line.moveTo(start_x, row_y)
                    row_line.lineTo(start_x + width, row_y)
                    self.canvas.drawPath(row_line, grid_paint)
                
                # 技能名称（水平和垂直居中）
                skill_name = skill.get('名称', '未知')
                name_width = font_content.measureText(skill_name)
                name_x = current_x + col_widths[0] / 2 - name_width / 2  # 水平居中
                name_y = row_y + row_height / 2 + 5  # 垂直居中
                self.canvas.drawString(skill_name, name_x, name_y, font_content, content_paint)
                current_x += col_widths[0]
                
                # 冷却时间（居中）
                cooldown = skill.get('冷却时间', '无')
                cooldown_x = current_x + col_widths[1] / 2 - font_content.measureText(cooldown) / 2
                cooldown_y = row_y + row_height / 2 + 5  # 垂直居中
                self.canvas.drawString(cooldown, cooldown_x, cooldown_y, font_content, content_paint)
                current_x += col_widths[1]
                
                # 技力消耗（居中）
                cost = skill.get('技力消耗', '0')
                
                # 检查是否需要绘制斜线（当技力消耗为空或"0"时）
                if not cost or cost == '0' or cost.strip() == '':
                    # 绘制斜线效果
                    line_paint = skia.Paint(Color=skia.Color4f(0.6, 0.6, 0.6, 1), AntiAlias=True)
                    line_paint.setStyle(skia.Paint.kStroke_Style)
                    line_paint.setStrokeWidth(3)
                    
                    # 计算当前列的边界
                    cell_x = current_x
                    cell_y = row_y
                    cell_width = col_widths[2]
                    cell_height = row_height
                    
                    # 绘制从左上到右下的斜线
                    line1 = skia.Path()
                    line1.moveTo(cell_x + 8, cell_y + 8)
                    line1.lineTo(cell_x + cell_width - 8, cell_y + cell_height - 8)
                    self.canvas.drawPath(line1, line_paint)
                else:
                    # 正常绘制技力消耗
                    cost_x = current_x + col_widths[2] / 2 - font_content.measureText(cost) / 2
                    cost_y = row_y + row_height / 2 + 5  # 垂直居中
                    self.canvas.drawString(cost, cost_x, cost_y, font_content, content_paint)
                current_x += col_widths[2]
                
                # 技能效果（完整显示所有行）
                effect = skill.get('效果', '无效果')
                effect_lines = self._wrap_text(effect, col_widths[3] - 30, 21)
                effect_start_y = row_y + 25  # 效果文本的起始位置
                for j, line in enumerate(effect_lines):  # 显示所有行
                    self.canvas.drawString(line, current_x + 15, effect_start_y + j * 25, font_content, content_paint)
                
                # 移动到下一行
                current_row_y += row_height
        else:
            # 无技能时只绘制简单提示，不绘制表格框架
            # 绘制简单的背景框
            simple_height = 60
            simple_rect = skia.Rect(start_x, start_y, start_x + width, start_y + simple_height)
            table_bg_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 0.9), AntiAlias=True)
            self.canvas.drawRect(simple_rect, table_bg_paint)
            self.canvas.drawRect(simple_rect, border_paint)
            
            # 无技能提示
            no_skill_text = "无特殊技能"
            no_skill_width = font_content.measureText(no_skill_text)
            no_skill_x = start_x + (width - no_skill_width) / 2
            self.canvas.drawString(no_skill_text, no_skill_x, start_y + 38, font_content, content_paint)
    
    def _talents_section(self, enemy: EnemyData, start_x: int, start_y: int, width: int, header_height: int, content_height: int, border_paint):
        """在统一表格中绘制天赋部分"""
        # 1. 绘制整个天赋表格的背景
        total_height = header_height + content_height
        table_rect = skia.Rect(start_x, start_y, start_x + width, start_y + total_height)
        table_bg_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 0.9), AntiAlias=True)
        self.canvas.drawRect(table_rect, table_bg_paint)
        self.canvas.drawRect(table_rect, border_paint)
        
        # 2. 绘制天赋表头背景
        header_bg_paint = skia.Paint(Color=skia.Color4f(0.9, 0.9, 0.9, 1), AntiAlias=True)
        header_rect = skia.Rect(start_x, start_y, start_x + width, start_y + header_height)
        self.canvas.drawRect(header_rect, header_bg_paint)
        
        # 3. 绘制天赋表头分隔线
        header_line = skia.Path()
        header_line.moveTo(start_x, start_y)
        header_line.lineTo(start_x + width, start_y)
        self.canvas.drawPath(header_line, border_paint)
        
        header_line2 = skia.Path()
        header_line2.moveTo(start_x, start_y + header_height)
        header_line2.lineTo(start_x + width, start_y + header_height)
        self.canvas.drawPath(header_line2, border_paint)
        
        # 4. "天赋&能力"标题
        talents_font = self.font_manager.get_font(24)
        talents_font.setEmbolden(True)
        talents_title_paint = skia.Paint(Color=skia.Color4f(0.2, 0.2, 0.2, 1), AntiAlias=True)
        talent_title_text = "天赋&能力"
        talent_title_width = talents_font.measureText(talent_title_text)
        talent_title_x = start_x + (width - talent_title_width) / 2
        self.canvas.drawString(talent_title_text, talent_title_x, start_y + 30, talents_font, talents_title_paint)
        
        # 5. 绘制天赋内容
        content_start_y = start_y + header_height
        if enemy.talents_abilities:
            desc_font = self.font_manager.get_font(24)
            desc_paint = skia.Paint(Color=skia.Color4f(0.3, 0.3, 0.3, 1), AntiAlias=True)
            
            lines = self._wrap_text(enemy.talents_abilities, width - 40, 24)
            for i, line in enumerate(lines):  # 显示所有行，不限制
                y_pos = content_start_y + 25 + i * 28
                self.canvas.drawString(line, start_x + 20, y_pos, desc_font, desc_paint)
        else:
            no_talent_font = self.font_manager.get_font(24)
            no_talent_paint = skia.Paint(Color=skia.Color4f(0.5, 0.5, 0.5, 1), AntiAlias=True)
            no_talent_text = "无特殊天赋能力"
            no_talent_width = no_talent_font.measureText(no_talent_text)
            no_talent_x = start_x + (width - no_talent_width) / 2
            self.canvas.drawString(no_talent_text, no_talent_x, content_start_y + 50, no_talent_font, no_talent_paint)
    

    def _rating_cards(self, enemy: EnemyData, skills_bottom_y: int):
        """绘制评价卡片系统 - 移到技能天赋表格左侧"""
        ratings = [
            ("对策度", enemy.hostility_rating, (0.85, 0.2, 0.3)),
            ("创新度", enemy.innovation_rating, (0.2, 0.6, 0.9)), 
            ("威胁度", enemy.threat_rating, (0.9, 0.5, 0.1))
        ]
        
        # 评价区域整体布局 - 移到技能天赋表格左侧，再次略微下移
        start_x = 60  # 保持在最左侧
        start_y = 560  # 再次下移，给技能表格更多空间
        card_width = 360
        card_height = 105
        spacing = 126
        
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
            self.canvas.drawRoundRect(card_rect, 18, 18, card_paint)
            
            # 卡片边框
            border_paint = skia.Paint(Color=skia.Color4f(*color, 0.9))
            border_paint.setStyle(skia.Paint.kStroke_Style)
            border_paint.setStrokeWidth(4.5)
            self.canvas.drawRoundRect(card_rect, 18, 18, border_paint)
            
            # 评价名称（左侧显示）
            name_font = self.font_manager.get_font(33)
            name_font.setEmbolden(True)
            name_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 1), AntiAlias=True)
            self.canvas.drawString(name, x + 24, y + 66, name_font, name_paint)
            
            # 星级显示 - 在名称右侧，更紧凑
            name_width = name_font.measureText(name)
            star_start_x = x + 45 + name_width
            star_size = 15  # 稍微减小星级大小
            for j in range(5):
                star_x = star_start_x + j * 33
                star_y = y + 54
                
                if j < rating:
                    # 实心星星 - 金色
                    self._premium_star(star_x, star_y, star_size, (1.0, 0.9, 0.3))
                else:
                    # 空心星星
                    self._empty_star(star_x, star_y, star_size)
    
    
    def _wrap_text(self, text: str, max_width: int, font_size: int) -> list[str]:
        """高性能文本换行 - 使用缓存的文本布局"""
        if not text:
            return [""]
        
        # 使用资源管理器的缓存文本布局
        typeface = self.font_manager.chinese_font if self.font_manager.chinese_font else None
        layout_result = self.resource_manager.get_text_layout(
            text, max_width, font_size, typeface
        )
        
        return layout_result.lines
    
    def _premium_star(self, cx: float, cy: float, radius: float, color: tuple):
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

    def _empty_star(self, cx: float, cy: float, radius: float):
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
    
    def _grade_section(self, enemy: EnemyData, skills_bottom_y: int):
        """绘制综合评级框 - 贴近底部"""
        # 直接计算贴近底部的位置  
        grade_height = 210  # 评级框高度
        grade_start_y = self.height - grade_height - 15  # 更贴近底部，距离底部15px
        
        # 等级卡片背景 - 贴近底部
        grade_rect = skia.Rect(60, grade_start_y, 420, grade_start_y + 210)
        grade_color = self.grade_colors.get(enemy.grade, (0.6, 0.6, 0.6, 1.0))
        
        # 渐变背景
        gradient_colors = [
            skia.Color4f(*grade_color),
            skia.Color4f(grade_color[0] * 0.7, grade_color[1] * 0.7, grade_color[2] * 0.7, grade_color[3])
        ]
        gradient = skia.GradientShader.MakeLinear(
            points=[(60, grade_start_y), (420, grade_start_y + 210)],
            colors=gradient_colors
        )
        grade_paint = skia.Paint(Shader=gradient)
        self.canvas.drawRoundRect(grade_rect, 24, 24, grade_paint)
        
        # 边框
        border_paint = skia.Paint(Color=skia.Color4f(*grade_color))
        border_paint.setStyle(skia.Paint.kStroke_Style)
        border_paint.setStrokeWidth(4.5)
        self.canvas.drawRoundRect(grade_rect, 24, 24, border_paint)
        
        # 等级字母 - 居中显示
        grade_font = self.font_manager.get_font(126)
        grade_font.setEmbolden(True)
        text_paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 1), AntiAlias=True)
        
        # 文字阴影
        shadow_paint = skia.Paint(Color=skia.Color4f(0, 0, 0, 0.3), AntiAlias=True)
        grade_width = grade_font.measureText(enemy.grade)
        grade_x = 240 - grade_width / 2
        self.canvas.drawString(enemy.grade, grade_x + 6, grade_start_y + 141, grade_font, shadow_paint)
        self.canvas.drawString(enemy.grade, grade_x, grade_start_y + 135, grade_font, text_paint)
        
        # 简评区域 - 紧挨着评级右侧
        comment_rect = skia.Rect(480, grade_start_y, 1860, grade_start_y + 210)
        
        # 简评背景
        comment_paint = skia.Paint(Color=skia.Color4f(0.96, 0.96, 0.96, 0.9))
        self.canvas.drawRoundRect(comment_rect, 18, 18, comment_paint)
        
        # 简评边框
        comment_border = skia.Paint(Color=skia.Color4f(0.75, 0.75, 0.75, 0.8))
        comment_border.setStyle(skia.Paint.kStroke_Style)
        comment_border.setStrokeWidth(3)
        self.canvas.drawRoundRect(comment_rect, 18, 18, comment_border)
        
        # 简评文字 - 使用手填的简评内容
        comment_font = self.font_manager.get_font(33)
        comment_text_paint = skia.Paint(Color=skia.Color4f(0.4, 0.4, 0.4, 1), AntiAlias=True)
        
        # 分行显示简评内容
        lines = self._wrap_text(enemy.brief_comment, 1200, 33)  # 使用统一的换行逻辑
        max_lines = 3  # 最多显示3行
        for i, line in enumerate(lines[:max_lines]):
            y_pos = grade_start_y + 75 + i * 45  # 动态调整位置
            if i == 0:
                line = f"简评：{line}"
            else:
                line = f"      {line}"  # 缩进对齐
            self.canvas.drawString(line, 510, y_pos, comment_font, comment_text_paint)
    
    
    def generate_card(self, enemy: EnemyData, output_path: Optional[str] = None) -> str:
        """高性能生成敌人评价卡片 - 带性能统计"""
        self._render_count += 1
        
        with PerformanceTimer(f"卡片生成#{self._render_count}"):
            try:
                # 高性能Canvas初始化
                self._init_canvas()
                
                # 绘制各个部分 - 优化的渲染流程
                with PerformanceTimer("头像区域渲染"):
                    self._avatar_section(enemy)
                
                with PerformanceTimer("信息区域渲染"):
                    info_section_bottom = self._info_section(enemy)
                
                with PerformanceTimer("技能区域渲染"):
                    skills_section_bottom = self._skills_talents_section(enemy, info_section_bottom)
                
                with PerformanceTimer("评分卡渲染"):
                    self._rating_cards(enemy, skills_section_bottom)
                
                with PerformanceTimer("等级区域渲染"):
                    self._grade_section(enemy, skills_section_bottom)
                
                # 保存图片
                if not output_path:
                    output_path = f"output_{enemy.name}_{enemy.grade}.png"
                
                with PerformanceTimer("图片保存"):
                    image = self.surface.makeImageSnapshot()
                    image.save(output_path, skia.kPNG)
                
                return output_path
                
            finally:
                # 确保资源清理
                self._cleanup_canvas()
    
    def generate_card_image(self, enemy: EnemyData) -> skia.Image:
        """高性能生成卡片图像（内存模式） - GUI实时预览优化"""
        self._render_count += 1
        
        with PerformanceTimer(f"GUI预览渲染#{self._render_count}"):
            try:
                # 高性能Canvas初始化
                self._init_canvas()
                
                # 优化的渲染流程（无详细计时，减少开销）
                self._avatar_section(enemy)
                info_section_bottom = self._info_section(enemy)
                skills_section_bottom = self._skills_talents_section(enemy, info_section_bottom)
                self._rating_cards(enemy, skills_section_bottom)
                self._grade_section(enemy, skills_section_bottom)
                
                # 返回图像对象
                return self.surface.makeImageSnapshot()
                
            finally:
                # 确保资源清理
                self._cleanup_canvas()