import json
import math
import random
import time
import numpy as np
from enum import Enum

from monsters import MonsterFactory
from utils import VIRTUAL_TIME_DELTA, BuffEffect, BuffType, Faction
from zone import PoisonZone

# 场景参数
MAP_SIZE = np.array([15, 9])  # 场景宽度（单位：格）
SPAWN_AREA = 2  # 阵营出生区域宽度


from collections import defaultdict

class SpatialHash:
    def __init__(self, cell_size=0.2):
        self.cell_size = cell_size
        self.grid = defaultdict(set)  # 使用集合避免重复
        self.position_map = {}  # 记录每个对象的当前位置键

    def _pos_to_key(self, position: tuple) -> tuple:
        """将坐标转换为网格键"""
        x, y = position
        return (
            int(math.floor(x / self.cell_size)),
            int(math.floor(y / self.cell_size))
        )

    def insert(self, obj_id: int, position: tuple):
        """插入或更新对象位置"""
        new_key = self._pos_to_key(position)
        
        # 如果位置未变化，直接返回
        if obj_id in self.position_map and self.position_map[obj_id] == new_key:
            return
        
        # 移除旧位置的记录
        if obj_id in self.position_map:
            old_key = self.position_map[obj_id]
            self.grid[old_key].discard(obj_id)
            if not self.grid[old_key]:  # 清理空单元格
                del self.grid[old_key]
        
        # 更新到新位置
        self.position_map[obj_id] = new_key
        self.grid[new_key].add(obj_id)

    def query_neighbors(self, position: tuple, radius: float) -> set:
        """查询指定半径内的邻居"""
        center_x, center_y = position
        search_radius = math.ceil(radius / self.cell_size)
        neighbors = set()
        
        # 生成需要检测的网格范围
        min_i = int((center_x - radius) / self.cell_size)
        max_i = int((center_x + radius) / self.cell_size)
        min_j = int((center_y - radius) / self.cell_size)
        max_j = int((center_y + radius) / self.cell_size)
        
        # 遍历所有可能包含邻居的网格
        for i in range(min_i, max_i + 1):
            for j in range(min_j, max_j + 1):
                neighbors.update(self.grid.get((i, j), set()))
                
        return neighbors

    def batch_update(self, updates: dict):
        """批量更新对象位置"""
        for obj_id, pos in updates.items():
            self.insert(obj_id, pos)

class Battlefield:
    def __init__(self, monster_data):
        self.monsters = []
        self.round = 0
        self.map_size = MAP_SIZE
        self.monster_data = monster_data
        self.globalId = 0
        self.effect_zones = []
        self.dead_count = {Faction.LEFT: 0, Faction.RIGHT: 0}

        self.effect_zones.append(PoisonZone(self))


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
    
    def check_zone(self):
        new_zone = []
        # 检查场地效果
        for zone in self.effect_zones:
            zone.update(VIRTUAL_TIME_DELTA)
            if zone.should_clear():
                continue
            for m in self.monsters:
                if zone.contains(m.position):
                    zone.apply_effect(m)
            new_zone.append(zone)
        self.effect_zones = new_zone

    def run_battle(self, visualize=False):
        """运行战斗直到决出胜负"""

        self.gameTime = 0
        while True:
            if visualize and self.round % 120 == 0:
                self.print_battlefield()
            self.round += 1

            self.check_zone()

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
    
    def add_new_zone(self, zone):
        self.effect_zones.append(zone)

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