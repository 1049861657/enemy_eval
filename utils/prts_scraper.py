"""
PRTS Wiki 敌人数据爬取器 - 完整集成版本
提供PRTS Wiki数据爬取、转换、预缓存的完整解决方案
"""

import logging
import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Any, Optional, Tuple
from urllib.parse import quote
from models import EnemyData

logger = logging.getLogger(__name__)


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
    
    @staticmethod
    def _preload_avatar_image(avatar_path: str):
        """预下载avatar图片到缓存，避免渲染时的网络阻塞"""
        if not avatar_path:
            return
        
        try:
            from utils.network_image import is_url, download_image_data, get_url_cache_key
            from core.optimization import _GLOBAL_IMAGE_CACHE
            
            # 只处理网络URL
            if not is_url(avatar_path):
                return
            
            # 预下载图片数据到系统缓存
            image_data = download_image_data(avatar_path)
            if image_data:
                cache_key = f"{get_url_cache_key(avatar_path)}_{(330, 330)}"
                
                # 创建Skia图像并直接缓存
                import skia
                original_image = skia.Image.MakeFromEncoded(image_data)
                if original_image:
                    # 直接缩放并缓存，避免渲染时重复处理
                    target_w, target_h = 330, 330
                    if (original_image.width(), original_image.height()) != (target_w, target_h):
                        scaled_surface = skia.Surface(target_w, target_h)
                        scaled_canvas = scaled_surface.getCanvas()
                        sampling = skia.SamplingOptions(skia.CubicResampler.Mitchell())
                        paint = skia.Paint()
                        paint.setAntiAlias(True)
                        
                        src_rect = skia.Rect(0, 0, original_image.width(), original_image.height())
                        dst_rect = skia.Rect(0, 0, target_w, target_h)
                        scaled_canvas.drawImageRect(original_image, src_rect, dst_rect, sampling, paint)
                        scaled_image = scaled_surface.makeImageSnapshot()
                    else:
                        scaled_image = original_image
                    
                    # 预存到全局图像缓存
                    _GLOBAL_IMAGE_CACHE[cache_key] = scaled_image
                    logger.info(f"成功预缓存avatar图片: {avatar_path}")
                    
        except Exception as e:
            # 预加载失败不影响主流程
            logger.warning(f"预加载avatar图片失败: {e}")
    
    @staticmethod
    def _convert_to_enemy_data(prts_data: Dict[str, Any], enemy_name: str) -> Optional[EnemyData]:
        """将PRTS数据转换为EnemyData格式"""
        try:
            # 基础字段映射和默认值
            converted_data = {
                'name': prts_data.get('name', enemy_name),
                'grade': 'C',  # 默认等级，需要用户手动设置
                'attack_type': prts_data.get('attack_type', '近战'),
                'damage_type': '物理',  # PRTS不提供此字段，使用默认值
                'action_type': prts_data.get('action_type', '地面'),
                'hp_recovery_speed': float(prts_data.get('hp_recovery_speed', 0) or 0),
                'position': prts_data.get('position', '普通'),
                'category': prts_data.get('category', '其他'),
                'max_hp': int(prts_data.get('max_hp', 1000) or 1000),
                'attack': int(prts_data.get('attack', 100) or 100),
                'defense': int(prts_data.get('defense', 50) or 50),
                'magic_resistance': int(prts_data.get('magic_resistance', 10) or 10),
                'attack_range_radius': float(prts_data.get('attack_range_radius', 0) or 0),
                'weight_level': int(prts_data.get('weight_level', 1) or 1),
                'move_speed': float(prts_data.get('move_speed', 1.0) or 1.0),
                'attack_interval': float(prts_data.get('attack_interval', 2.0) or 2.0),
                'damage_resistance': int(prts_data.get('damage_resistance', 0) or 0),
                'element_resistance': int(prts_data.get('element_resistance', 0) or 0),
                'base_taunt_level': int(prts_data.get('base_taunt_level', 0) or 0),
                'target_value': int(prts_data.get('target_value', 1) or 1),
                'brief_description': prts_data.get('brief_description', f"来自PRTS的{enemy_name}数据"),
                'brief_comment': '待评价',  # 需要用户填写
                'abnormal_resistances': {},  # PRTS不提供此数据
                'hostility_rating': 3,  # 默认评级
                'innovation_rating': 3,
                'threat_rating': 3,
                'avatar_path': prts_data.get('avatar_path'),
                'skills': [],  # PRTS不提供技能数据
                'talents_abilities': ''  # PRTS不提供天赋数据
            }
            
            # 创建EnemyData实例
            return EnemyData(**converted_data)
            
        except Exception as e:
            logger.error(f"数据转换失败: {e}")
            return None
    
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
    
    def _scrape_url(self, url: str, enemy_name: str) -> Dict[str, Any]:
        """爬取指定URL的数据，同时获取头像信息"""
        try:
            # 使用Session复用连接
            with requests.Session() as session:
                session.headers.update(self.headers)
                
                # 获取主页面数据
                response = session.get(url, timeout=10)
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
                
                # 在同一会话中获取头像URL
                avatar_url = self._get_avatar_url_with_session(session, enemy_name)
                if avatar_url:
                    result['avatar_path'] = avatar_url
                
                return result
            
        except Exception as e:
            return {'error': str(e), 'error_type': 'scraping_error'}
    
    def _get_avatar_url_with_session(self, session: requests.Session, enemy_name: str) -> Optional[str]:
        """使用现有会话获取敌人头像URL"""
        try:
            # 构建文件页面URL
            file_url = f"{self.base_url}文件:头像_敌人_{quote(enemy_name)}.png"
            
            response = session.get(file_url, timeout=3)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 寻找页面主要区域的第一个media.prts.wiki链接
            main_content = soup.find('div', {'id': 'mw-content-text'}) or soup
            links = main_content.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                # 查找完整的media.prts.wiki URL，排除缩略图，支持URL编码
                if ('media.prts.wiki' in href and 
                    ('%E5%A4%B4%E5%83%8F_%E6%95%8C%E4%BA%BA_' in href or '头像_敌人_' in href) and 
                    '/thumb/' not in href and
                    href.endswith('.png')):
                    # 清理URL，移除时间戳参数
                    clean_url = href.split('?')[0]
                    return clean_url
                
            return None
            
        except Exception as e:
            return None


def fetch_enemy_data(enemy_name: str) -> Tuple[Optional[EnemyData], Optional[str]]:
    """
    完整的PRTS敌人数据获取和转换接口
    
    Args:
        enemy_name: 敌人名称
        
    Returns:
        tuple: (转换后的EnemyData对象, 错误信息)
              如果成功返回 (EnemyData, None)
              如果失败返回 (None, 错误信息)
    """
    try:
        scraper = PRTSScraper()
        
        # 构建URL
        encoded_name = quote(enemy_name)
        url = f"{scraper.base_url}{encoded_name}"
        
        # 爬取数据(包含头像获取)
        prts_data = scraper._scrape_url(url, enemy_name)
        
        # 检查是否有错误
        if 'error' in prts_data:
            error_msg = prts_data.get('error', '未知错误')
            if '404' in error_msg:
                return None, f"在PRTS中未找到敌人「{enemy_name}」，请检查名称是否正确。"
            else:
                return None, f"获取PRTS数据失败：{error_msg}"
        
        # 如果爬取成功但没有名称，则设置名称
        if 'name' not in prts_data:
            prts_data['name'] = enemy_name
        
        # 预下载avatar图片到缓存
        if 'avatar_path' in prts_data:
            PRTSScraper._preload_avatar_image(prts_data['avatar_path'])
        
        # 转换数据格式
        enemy_data = PRTSScraper._convert_to_enemy_data(prts_data, enemy_name)
        
        if enemy_data:
            return enemy_data, None
        else:
            return None, "PRTS数据格式不兼容，无法导入。"
            
    except Exception as e:
        logger.error(f"PRTS数据获取失败: {e}")
        return None, f"获取PRTS数据时发生错误：{str(e)}"


# 向后兼容：保留原始字典接口
def fetch_enemy_data_raw(enemy_name: str) -> Dict[str, Any]:
    """
    获取原始PRTS数据字典（向后兼容接口）
    
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
    result = scraper._scrape_url(url, enemy_name)
    
    # 如果爬取成功但没有名称，则设置名称
    if 'error' not in result and 'name' not in result:
        result['name'] = enemy_name
    
    return result