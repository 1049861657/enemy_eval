"""
PRTS数据集成工具 - 负责PRTS数据获取和转换
"""

import logging
from typing import Optional, Dict, Any
from models import EnemyData
from .prts_scraper import fetch_enemy_data

logger = logging.getLogger(__name__)


class PRTSIntegration:
    """PRTS数据集成工具类 - 专门处理PRTS数据的获取和转换"""
    
    @staticmethod
    def fetch_and_convert(enemy_name: str) -> tuple[Optional[EnemyData], Optional[str]]:
        """
        获取并转换PRTS数据
        
        Args:
            enemy_name: 敌人名称
            
        Returns:
            tuple: (转换后的EnemyData对象, 错误信息)
                  如果成功返回 (EnemyData, None)
                  如果失败返回 (None, 错误信息)
        """
        try:
            # 获取PRTS数据
            prts_data = fetch_enemy_data(enemy_name)
            
            # 检查是否有错误
            if 'error' in prts_data:
                error_msg = prts_data.get('error', '未知错误')
                if '404' in error_msg:
                    return None, f"在PRTS中未找到敌人「{enemy_name}」，请检查名称是否正确。"
                else:
                    return None, f"获取PRTS数据失败：{error_msg}"
            
            # 转换数据格式
            enemy_data = PRTSIntegration._convert_prts_to_enemy_data(prts_data, enemy_name)
            
            if enemy_data:
                return enemy_data, None
            else:
                return None, "PRTS数据格式不兼容，无法导入。"
                
        except Exception as e:
            logger.error(f"PRTS数据获取失败: {e}")
            return None, f"获取PRTS数据时发生错误：{str(e)}"
    
    @staticmethod
    def _convert_prts_to_enemy_data(prts_data: Dict[str, Any], enemy_name: str) -> Optional[EnemyData]:
        """
        将PRTS数据转换为EnemyData格式
        
        Args:
            prts_data: PRTS原始数据
            enemy_name: 敌人名称
            
        Returns:
            转换后的EnemyData对象，失败返回None
        """
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
                'avatar_path': None,
                'skills': [],  # PRTS不提供技能数据
                'talents_abilities': ''  # PRTS不提供天赋数据
            }
            
            # 创建EnemyData实例
            return EnemyData(**converted_data)
            
        except Exception as e:
            logger.error(f"数据转换失败: {e}")
            return None
    
    @staticmethod 
    def get_field_mapping() -> Dict[str, str]:
        """
        获取PRTS字段到EnemyData字段的映射关系
        
        Returns:
            字段映射字典
        """
        return {
            'name': 'name',
            'attack_type': 'attack_type', 
            'action_type': 'action_type',
            'hp_recovery_speed': 'hp_recovery_speed',
            'position': 'position',
            'category': 'category',
            'max_hp': 'max_hp',
            'attack': 'attack',
            'defense': 'defense',
            'magic_resistance': 'magic_resistance',
            'attack_range_radius': 'attack_range_radius',
            'weight_level': 'weight_level',
            'move_speed': 'move_speed',
            'attack_interval': 'attack_interval',
            'damage_resistance': 'damage_resistance',
            'element_resistance': 'element_resistance',
            'base_taunt_level': 'base_taunt_level',
            'target_value': 'target_value',
            'brief_description': 'brief_description'
        }