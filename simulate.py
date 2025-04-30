import json
import math
import random
import time
from enum import Enum
import numpy as np
import pandas as pd
from tqdm import tqdm

from battle_field import Battlefield, Faction

# ID与怪物名称映射表 
MONSTER_MAPPING = {
    0: "狗pro",
    1: "酸液源石虫",
    2: "大盾哥",
    3: "萨卡兹大剑手",
    4: "高能源石虫",
    5: "宿主流浪者",
    6: "庞贝",
    7: "1750哥",
    8: "石头人",
    9: "鳄鱼",
    10: "保鲜膜",
    11: "拳击囚犯",
    12: "阿咬",
    13: "大喷蛛",
    14: "船长",
    15: "Vvan",
    16: "冰原术师",
    17: "萨卡兹链术师",
    18: "高塔术师",
    19: "萨克斯",
    20: "食腐狗",
    21: "镜神",
    22: "光剑",
    23: "绵羊",
    24: "雪球",
    25: "鼠鼠",
    26: "驮兽",
    27: "杰斯顿",
    28: "自在",
    29: "狼神",
    30: "雷德",
    31: "海螺",
    32: "污染躯壳",
    33: "矿脉守卫",
    # 根据实际数据继续扩展...
}

def process_battle_data(csv_path):
    """
    处理战斗数据CSV文件
    :param csv_path: 输入CSV文件路径
    """
    # 读取CSV文件（假设没有表头）
    df = pd.read_csv(csv_path, header=1)
    
    # 数据结构化处理
    battle_records = []
    
    for _, row in df.iterrows():
        # 分解左右阵营数据
        left_data = row[0:34]    # 1-34列 (0-based索引0-33)
        right_data = row[34:68]  # 35-68列 (0-based索引34-67)
        winner = row[68]         # 69列 (0-based索引68)
        
        # 构建阵营字典（ID从1开始）
        left_army = {MONSTER_MAPPING[i]: int(count) for i, count in enumerate(left_data) if count > 0}
        right_army = {MONSTER_MAPPING[i]: int(count) for i, count in enumerate(right_data) if count > 0}
        
        # 构建记录格式
        battle_record = {
            "left": left_army,
            "right": right_army,
            "result": "left" if winner == 'L' else "right"
        }
        
        battle_records.append(battle_record)
    
    return battle_records

def main():
    """主函数"""
    # 加载怪物数据
    with open("monsters.json", encoding='utf-8') as f:
        monster_data = json.load(f)["monsters"]
    
    # with open("scene.json", encoding='utf-8') as f:
    #     scene_config = json.load(f)

    # 使用示例
    battle_data = process_battle_data("arknights.csv")

    
    win = 0
    matches = 0
    for scene_config in tqdm(battle_data):
        #scene_config = {"left": {"1750哥": 5, "矿脉守卫": 6}, "right": {"高能源石虫": 22, "绵羊": 12}, "result": "right"}

        # 用户配置
        left_army = scene_config["left"]
        right_army = scene_config["right"]
    
        # 初始化战场
        battlefield = Battlefield(monster_data)
        if not battlefield.setup_battle(left_army, right_army, monster_data):
            continue
        
        left_win = False
        # 开始战斗
        if battlefield.run_battle(visualize=False) == Faction.LEFT:
            left_win = True
        
        if (left_win and scene_config["result"] == "left") or (not left_win and scene_config["result"] == "right"):
            win += 1
        else:
            with open("errors.json", encoding='utf-8', mode='+a') as f:
                f.write(json.dumps(scene_config, ensure_ascii=False))
                f.write('\n')
        

        matches += 1
        print(f"当前胜率：{win} / {matches}")
        #break
if __name__ == "__main__":
    # profiler = cProfile.Profile()
    # profiler.enable()
    main()
    # profiler.disable()
    # profiler.dump_stats('profile.stats')
   