#!/usr/bin/env python3
"""
敌人评价卡片生成器主程序
使用2025年最新技术栈：Skia-Python + Pydantic V2
"""

from pathlib import Path
from rich.console import Console
from rich.progress import track

from card_generator import EnemyCardGenerator
from models import EnemyData

console = Console()

def main():
    """主程序入口"""
    console.print("[bold green]🎮 敌人评价卡片生成器 v0.1.0[/bold green]")
    console.print("[dim]Powered by Skia-Python & 2025最新技术栈[/dim]\n")
    
    # 示例数据
    enemy_data = EnemyData(
        name="鸟",
        attack_type="近程",
        action_type="地面", 
        hp_recovery_speed=0,
        position="普通",
        category="无", 
        max_hp=7000,
        attack=350,
        defense=100,
        magic_resistance=10,
        attack_range_radius=1.0,
        weight_level=3,
        move_speed=1.0,
        attack_interval=3.5,
        damage_resistance=0,
        element_resistance=0,
        base_taunt_level=0,
        target_value=1,
        brief_description="生命值略高的敌人，但攻击力为0，行动速度快，在有限空间内无法奈何任何近战者",
        brief_comment="太菜了，略过",
        abnormal_resistances={
            "冰冻": 1,
            "沉默": 0,
            "晕眩": 1,
            "沉睡": 0,
            "浮空": 1,
            "战栗": 0,
            "恐惧": 0,
            "诱导": 1
        },  
        hostility_rating=1,  # 1-5星
        innovation_rating=2,  # 1-5星
        threat_rating=1,     # 1-5星
        grade="D",
        avatar_path="example/下载.jpg"
    )
    
    # 创建生成器
    generator = EnemyCardGenerator()
    
    # 生成卡片
    console.print("[yellow]正在生成敌人评价卡片...[/yellow]")
    
    output_path = generator.generate_card(enemy_data)
    
    console.print(f"[bold green]✅ 卡片生成完成！[/bold green]")
    console.print(f"[blue]保存路径: {output_path}[/blue]")

if __name__ == "__main__":
    main()