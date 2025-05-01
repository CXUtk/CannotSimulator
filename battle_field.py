import json
import math
import random
import time
import numpy as np
from enum import Enum

from monsters import Monster, MonsterFactory
from utils import BuffEffect, BuffType, Faction

# 场景参数
MAP_SIZE = np.array([15, 9])  # 场景宽度（单位：格）
SPAWN_AREA = 2  # 阵营出生区域宽度

VIRTUAL_TIME_STEP = 60 # 60帧相当于一秒
VIRTUAL_TIME_DELTA = 1.0 / VIRTUAL_TIME_STEP

class Battlefield:
    def __init__(self, monster_data):
        self.monsters = []
        self.round = 0
        self.map_size = MAP_SIZE
        self.monster_data = monster_data
        self.globalId = 0


    def append_monster(self, monster):
        """添加一个怪物到战场"""
        id = self.globalId
        monster.id = id
        self.globalId += 1
        self.monsters.append(monster)
    
    def append_monster_name(self, name, faction, pos):
        """添加一个怪物到战场，只需要名字"""
        data = next((m for m in self.monster_data if m["名字"] == name), None)
        id = self.globalId
        monster = MonsterFactory.create_monster(data, faction, pos, self)
        monster.id = id
        self.globalId += 1
        self.monsters.append(monster)

    def setup_battle(self, left_army, right_army, monster_data):
        """二维战场初始化"""
        # 左阵营生成在左上区域
        for (name, count) in left_army.items():
            data = next((m for m in monster_data if m["名字"] == name), None)
            if data is None:
                return False
            for _ in range(count):
                pos = np.array([
                    random.uniform(0, 1),
                    random.uniform(0, MAP_SIZE[1])
                ])
                self.append_monster(
                    MonsterFactory.create_monster(data, Faction.LEFT, pos, self)
                )
        
        # 右阵营生成在右下区域
        for (name, count) in right_army.items():
            data = next((m for m in monster_data if m["名字"] == name), None)
            if data is None:
                return False
            for _ in range(count):
                pos = np.array([
                    random.uniform(MAP_SIZE[0]-SPAWN_AREA, MAP_SIZE[0]),
                    random.uniform(0, MAP_SIZE[1])
                ])
                self.append_monster(
                    MonsterFactory.create_monster(data, Faction.RIGHT, pos, self)
                )
        
        return True

    def get_enemies(self, faction):
        """获取指定阵营的所有敌人"""
        return [m for m in self.monsters 
                if m.is_alive and m.faction != faction]

    def check_victory(self):
        """检查胜利条件"""
        alive_factions = set()
        for m in self.monsters:
            if m.is_alive:
                alive_factions.add(m.faction)
        
        if len(alive_factions) == 1:
            return list(alive_factions)[0]
        elif len(alive_factions) == 0:
            return Faction.LEFT
        return None

    def run_battle(self, visualize=False):
        """运行战斗直到决出胜负"""

        self.gameTime = 0
        while True:
            if visualize and self.round % 120 == 0:
                self.print_battlefield()
            self.round += 1
            # 计算毒圈
            if self.danger_zone_size() > 0:
                size = self.danger_zone_size()
                for m in self.monsters:
                    if (m.position[0] < size or m.position[0] > self.map_size[0] - size)\
                          or (m.position[1] < size or m.position[1] > self.map_size[1] - size):
                        m.status_system.apply(BuffEffect(
                            type=BuffType.POWER_STONE,
                            duration=VIRTUAL_TIME_DELTA * 2,
                            source=self
                        ))

            # 更新所有单位
            for m in self.monsters:
                m.update(VIRTUAL_TIME_DELTA)
            
            # 检查胜利条件
            winner = self.check_victory()
            self.monsters = [m for m in self.monsters if m.is_alive]
            if winner:
                print(f"\nVictory for {winner.name}!")
                left = len([m for m in self.monsters if m.is_alive and m.faction == Faction.LEFT])
                print(f"左边存活{left} / 右边存活{len(self.monsters) - left}")
                return winner
            
            self.gameTime += VIRTUAL_TIME_DELTA

    def danger_zone_size(self):
        if self.gameTime < 60:
            return 0
        return int((self.gameTime - 60) / 20) + 1
        

    def print_battlefield(self):
        """二维战场可视化"""
        grid = np.full((MAP_SIZE[1] * 2, MAP_SIZE[0] * 2), '.', dtype='U2')
        
        for m in self.monsters:
            if m.is_alive:
                x = np.minimum(np.maximum(0, int(m.position[0] * 2)), MAP_SIZE[0]*2-1)
                y = np.minimum(np.maximum(0, int(m.position[1] * 2)), MAP_SIZE[1]*2-1)
                symbol = 'L' if m.faction == Faction.LEFT else 'R'
                if grid[y, x] != '.' and symbol != grid[y, x]:
                    symbol = 'X'
                if m.char_icon != "":
                    symbol = m.char_icon
                grid[y, x] = symbol
        
        print(f"\nRound {self.round}")
        for row in grid:
            print(' '.join(row))

    def get_grid(self, target):
        x, y = int(target.position[0]), int(target.position[1])
        return x, y