"""
PRTS Wiki 敌人数据爬取器 - 精简重构版本
提供单一接口用于爬取PRTS Wiki的敌人数据
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Any, Optional
from urllib.parse import quote


class PRTSScraper:
    """精简的PRTS Wiki敌人数据爬取器"""
    
    def __init__(self):
        self.base_url = "https://prts.wiki/w/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # 官方种类列表
        self.valid_categories = [
            '感染生物', '无人机', '萨卡兹', '宿主', '海怪',
            '法术造物', '源石造物', '化物', '机械', '野生动物', '坍塌体', '其他'
        ]
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())
    
    def _extract_numeric_value(self, text: str) -> Optional[str]:
        """从文本中提取数值（与原版保持一致，返回字符串）"""
        if not text or text == "—" or text == "-":
            return None
        # 提取数字部分（包括小数）
        match = re.search(r'(\d+\.?\d*)', text)
        return match.group(1) if match else text
    
    def _clean_field_name(self, text: str) -> str:
        """专门清理字段名，移除工具提示内容"""
        if not text:
            return ""
        # 移除多余的空白字符和换行
        text = re.sub(r'\s+', ' ', text.strip())
        # 移除工具提示内容（通常在第一个中文词后有很长的解释）
        # 匹配模式：核心词 + 长解释文本
        cleaned = re.sub(r'^([^\s]+(?:\s[^\s]{1,3})?)\s.*', r'\1', text)
        return cleaned if cleaned else text
    
    def _extract_category(self, text: str) -> Optional[str]:
        """提取种类信息"""
        if not text:
            return None
        clean_text = self._clean_text(text)
        return clean_text if clean_text in self.valid_categories else None
    
    def _parse_data_table(self, table) -> Dict[str, Any]:
        """解析数据表格"""
        data = {}
        rows = table.find_all('tr')
        
        # 字段映射表
        field_map = {
            '名称': 'name',
            '地位': 'position', 
            '种类': 'category',
            '攻击方式': 'attack_type',
            '行动方式': 'action_type',
            '生命自回速度': 'hp_recovery_speed',
            '最大生命值': 'max_hp',
            '攻击力': 'attack',
            '防御力': 'defense',
            '法术抗性': 'magic_resistance',
            '攻击范围半径': 'attack_range_radius',
            '重量': 'weight_level',
            '移动速度': 'move_speed',
            '攻击间隔': 'attack_interval',
            '损伤抵抗': 'damage_resistance',
            '元素抗性': 'element_resistance',
            '基础嘲讽等级': 'base_taunt_level',
            '目标价值': 'target_value'
        }
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue
                
            # 处理描述信息（在级别0表格中的"描述"行）
            if len(cells) == 1:
                cell_text = self._clean_text(cells[0].get_text())
                if cell_text == '描述':
                    # 查找下一行的描述内容
                    next_row = row.find_next_sibling('tr')
                    if next_row:
                        next_cells = next_row.find_all(['td', 'th'])
                        if len(next_cells) == 1:
                            description = self._clean_text(next_cells[0].get_text())
                            if description and description != '描述':
                                data['brief_description'] = description
                    continue
            
                
            # 处理基本信息行（名称、地位、种类）
            if len(cells) >= 2:
                cell_texts = [self._clean_text(cell.get_text()) for cell in cells]
                
                # 检查是否为数据行
                if (len(cell_texts) >= 2 and 
                    cell_texts[0] and cell_texts[0] not in ['名称', '地位', '种类'] and
                    cell_texts[1] and cell_texts[1] in ['普通', '精英', '领袖']):
                    
                    data['name'] = cell_texts[0]
                    data['position'] = cell_texts[1]
                    
                    if len(cell_texts) > 2:
                        data['category'] = self._extract_category(cell_texts[2])
            
            # 特殊处理：6列数据行（攻击方式 近战 行动方式 地面 生命自回速度 0）
            if len(cells) == 6:
                try:
                    # 按照固定模式解析
                    if '攻击方式' in cells[0].get_text():
                        data['attack_type'] = self._clean_text(cells[1].get_text())
                        data['action_type'] = self._clean_text(cells[3].get_text())
                        data['hp_recovery_speed'] = self._extract_numeric_value(cells[5].get_text())
                        continue
                except:
                    pass
            
            # 处理主要属性行（6列数据）
            if len(cells) == 6 and any('生命值' in cell.get_text() for cell in cells):
                try:
                    # 第一行：最大生命值 攻击力 防御力 法术抗性 攻击范围半径 重量
                    headers = [self._clean_field_name(cell.get_text()) for cell in cells]
                    # 读取下一行数据
                    next_row = row.find_next_sibling('tr')
                    if next_row:
                        values = next_row.find_all(['td', 'th'])
                        if len(values) == 6:
                            for i, (header, value_cell) in enumerate(zip(headers, values)):
                                clean_header = header
                                field_name = field_map.get(clean_header, clean_header)
                                value = self._clean_text(value_cell.get_text())
                                
                                if field_name in ['max_hp', 'attack', 'defense', 'magic_resistance', 'weight_level', 'hp_recovery_speed', 'base_taunt_level']:
                                    data[field_name] = self._extract_numeric_value(value)
                                elif field_name in ['move_speed', 'attack_interval', 'target_value']:
                                    data[field_name] = self._extract_numeric_value(value)
                                elif field_name == 'attack_range_radius' and value in ['—', '-']:
                                    data[field_name] = None
                                elif value and value not in ['—', '-', '']:
                                    data[field_name] = value
                except:
                    pass
            
            # 处理第二行属性（移动速度等）
            elif len(cells) == 6 and any('移动速度' in cell.get_text() for cell in cells):
                try:
                    headers = [self._clean_field_name(cell.get_text()) for cell in cells]
                    # 读取下一行数据
                    next_row = row.find_next_sibling('tr')
                    if next_row:
                        values = next_row.find_all(['td', 'th'])
                        if len(values) == 6:
                            for i, (header, value_cell) in enumerate(zip(headers, values)):
                                clean_header = header
                                field_name = field_map.get(clean_header, clean_header)
                                value = self._clean_text(value_cell.get_text())
                                
                                if field_name in ['move_speed', 'attack_interval', 'target_value']:
                                    data[field_name] = self._extract_numeric_value(value)
                                elif field_name in ['damage_resistance', 'element_resistance', 'base_taunt_level']:
                                    data[field_name] = self._extract_numeric_value(value)
                                elif value and value not in ['—', '-', '']:
                                    data[field_name] = value
                except:
                    pass
        
        return data
    
    def _scrape_url(self, url: str) -> Dict[str, Any]:
        """爬取指定URL的数据"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            result = {}
            
            # 查找并解析所有相关表格
            tables = soup.find_all('table')
            for table in tables:
                table_text = table.get_text()
                
                # 基本信息表格或属性表格
                if ('级别0' in table_text or 
                    ('名称' in table_text and '地位' in table_text) or
                    '最大生命值' in table_text):
                    
                    parsed_data = self._parse_data_table(table)
                    result.update(parsed_data)
            
            return result
            
        except Exception as e:
            return {'error': str(e), 'error_type': 'scraping_error'}


def fetch_enemy_data(enemy_name: str) -> Dict[str, Any]:
    """
    根据敌人名称爬取PRTS Wiki数据
    
    Args:
        enemy_name: 敌人名称
        
    Returns:
        包含敌人数据的字典，如果失败则包含错误信息
    """
    scraper = PRTSScraper()
    
    # 构建URL
    encoded_name = quote(enemy_name)
    url = f"{scraper.base_url}{encoded_name}"
    
    # 爬取数据
    result = scraper._scrape_url(url)
    
    # 如果爬取成功但没有名称，则设置名称
    if 'error' not in result and 'name' not in result:
        result['name'] = enemy_name
    
    return result