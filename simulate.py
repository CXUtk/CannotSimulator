import json
import math
import random
import time
from enum import Enum
import numpy as np
import pandas as pd
from tqdm import tqdm

from .battle_field import Battlefield, Faction
from .utils import DEBUG

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
    25: "鼠鼠",
    24: "雪球",
    26: "驮兽",
    27: "杰斯顿",
    28: "自在",
    29: "狼神",
    30: "雷德",
    31: "海螺",
    32: "污染躯壳",
    33: "矿脉守卫",
    34: "炮god",
    35: "红刀哥",
    36: "大斧",
    37: "护盾哥",
    38: "冰爆虫",
    39: "机鳄",
    40: "沸血骑士",
    41: "衣架",
    42: "畸变之矛",
    43: "榴弹佣兵",
    44: "标枪恐鱼",
    45: "雪境精锐",
    46: "狂躁珊瑚",
    47: "拳击手",
    48: "洗地车",
    49: "凋零萨卡兹",
    50: "高普尼克",
    51: "跑男",
    52: "门",
    53: "小锤",
    54: "爱蟹者",
    55: "酒桶",
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
        left_data = row[0:56]    # 1-56列 (0-based索引0-55)
        right_data = row[56:112]  # 56-112列 (0-based索引56-111)
        winner = row[112]         # 69列 (0-based索引112)
        
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

    # 使用示例，直接修改这里的csv文件就可以跑模拟
    battle_data = process_battle_data("arknights-new.csv")

    VISUALIZATION_MODE = True
    DEBUG = VISUALIZATION_MODE

    
    win = 0
    matches = 0
    for scene_config in tqdm(battle_data):
        scene_config = { "left": { "宿主流浪者": 6, "小锤": 0, "光剑":0 }, "right": { "鳄鱼": 10, "1750哥": 0, "炮god": 0 }, "result": "right" }



        #{ "left": { "护盾哥": 5, "污染躯壳": 11, "船长": 5 }, "right": { "炮god": 4, "沸血骑士": 4, "雪境精锐": 4}, "result": "left" }

        # 用户配置
        left_army = scene_config["left"]
        right_army = scene_config["right"]
    
        # 初始化战场
        battlefield = Battlefield(monster_data)
        if not battlefield.setup_battle(left_army, right_army, monster_data):
            continue
        
        left_win = False
        # 开始战斗
        if battlefield.run_battle(visualize=VISUALIZATION_MODE) == Faction.LEFT:
            left_win = True
        
        if (left_win and scene_config["result"] == "left") or (not left_win and scene_config["result"] == "right"):
            win += 1
        else:
            with open("errors.json", encoding='utf-8', mode='+a') as f:
                f.write(json.dumps(scene_config, ensure_ascii=False))
                f.write('\n')
        

        matches += 1
        print(f"当前胜率：{win} / {matches}")
        break


if __name__ == "__main__":
    main()
   