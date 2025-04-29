import json
import math
import random
import time
from enum import Enum
import numpy as np

from battle_field import Battlefield, Faction


# 用户交互部分
def setup_army(monster_list, faction_name):
    print(f"\n设置 {faction_name} 阵营:")
    army = {}
    for m in monster_list:
        count = input(f"请输入 [{m['名字']}] 的数量 (0-5): ")
        army[m['名字']] = int(count)
    return army

if __name__ == "__main__":
    # 加载怪物数据
    with open("monsters.json", encoding='utf-8') as f:
        monster_data = json.load(f)["monsters"]
    
    with open("scene.json", encoding='utf-8') as f:
        scene_config = json.load(f)

    # 用户配置
    left_army = scene_config["left"]
    right_army = scene_config["right"]
    
    MATCHES = 1

    left_win = 0
    for i in range(MATCHES):
        # 初始化战场
        battlefield = Battlefield()
        battlefield.setup_battle(left_army, right_army, monster_data)

        # 开始战斗
        if battlefield.run_battle(visualize=True) == Faction.LEFT:
            left_win += 1
    
    print(f"\n战斗结果：左边胜率：{left_win / MATCHES:2f}")