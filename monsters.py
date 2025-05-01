from dataclasses import dataclass, field
import json
import math
import random
import time
from enum import Enum
from typing import List
import numpy as np

from elemental import ElementAccumulator, ElementType
from utils import BuffEffect, BuffType, debug_print, Faction



def calculate_normal_dmg(defense, magic_resist, dmg, magic=False):
    """计算伤害值"""
    if not magic:
        return np.maximum(1, np.maximum(dmg - defense, dmg * 0.05))
    elif magic:
        return np.maximum(dmg * 0.05, dmg * (1.0 - magic_resist / 100))
    
def manhatton_distance(pos1, pos2):
    a_x = int(pos1[0])
    a_y = int(pos1[1])

    b_x = int(pos2[0])
    b_y = int(pos2[1])
    return abs(a_x - b_x) + abs(a_y - b_y)

class TargetSelector:
    @staticmethod
    def select_targets(attacker, battlefield, need_in_range=False, max_targets=2):
        """
        带嘲讽等级的目标选择算法
        优先级: 攻击范围内最高嘲讽等级 > 同等级最近目标 > 全局最近目标
        """
        # 获取所有有效敌人
        enemies : list[Monster] = [m for m in battlefield.monsters 
                   if m.is_alive 
                   and m.faction != attacker.faction]
        
        if not enemies:
            return []
        
        # 计算所有敌人属性
        enemy_info = []
        for enemy in enemies:
            dist = np.linalg.norm(enemy.position - attacker.position)
            in_range = dist <= attacker.attack_range

            if not need_in_range or (need_in_range and in_range):
                enemy_info.append({
                    "enemy": enemy,
                    "distance": dist,
                    "aggro": enemy.aggro if in_range else 0 
                })
        
        # 按照优先级排序：嘲讽降序 -> 距离升序
        sorted_enemies = sorted(enemy_info,
            key=lambda x: (-x["aggro"], x["distance"]))

        count = np.minimum(max_targets, len(sorted_enemies))
        # 选择前N个目标
        return [e["enemy"] for e in sorted_enemies[:count]]

class StatusSystem:
    def __init__(self, owner):
        self.owner : Monster = owner
        self.effects = []
        self.original_attributes = {}

        self.fire_dmg_counter = 0
        self.corrupt_dmg_counter = 0
        self.power_stay_counter = 0
        
    def apply(self, effect):
        # 处理效果叠加逻辑
        existing = next((e for e in self.effects if e.type == effect.type), None)

        # # 已经冰冻住了就不要施加寒冷效果了
        # if effect.type == BuffType.CHILL:
        #     if next((e for e in self.effects if e.type == BuffType.FROZEN), None):
        #         return
        
        if existing:
            # 寒冷效果叠加就会变成冰冻
            if effect.type == BuffType.CHILL:
                self.remove(existing)
                self.apply(BuffEffect(BuffType.FROZEN, effect.duration, effect.source, effect.stacks, effect.data))
                debug_print(f"{self.owner.name}{self.owner.id} 被 {effect.source.name} 冰冻了！")
                return

            # 其他效果刷新时间
            existing.duration = max(existing.duration, effect.duration)
        else:
            self._init_effect(effect)
            self.effects.append(effect)

    def update(self, delta_time):
        new_effects = []
        for effect in self.effects:
            effect.duration -= delta_time
            if effect.duration > 0:
                new_effects.append(effect)
            else:
                self.remove(effect)

        self.effects = new_effects
                
        # 处理持续伤害
        self._process_dot(delta_time)

    def _process_dot(self, delta_time):
        fire = next((e for e in self.effects if e.type == BuffType.FIRE), None)
        if fire:
            # 每秒造成伤害
            self.fire_dmg_counter += delta_time
            if self.fire_dmg_counter >= 0.33:
                self.fire_dmg_counter = 0
                damage = calculate_normal_dmg(0, self.owner.magic_resist, 20, True)
                self.owner.take_damage(damage)

        corrupt = next((e for e in self.effects if e.type == BuffType.CORRUPT), None)
        if corrupt:
            # 每秒造成伤害
            self.corrupt_dmg_counter += delta_time
            if self.corrupt_dmg_counter >= 1:
                self.corrupt_dmg_counter = 0
                damage = calculate_normal_dmg(0, self.owner.magic_resist, 100, True)
                self.owner.take_damage(damage)

        power_stone = next((e for e in self.effects if e.type == BuffType.POWER_STONE), None)
        if power_stone:
            self.power_stay_counter += delta_time
            if self.corrupt_dmg_counter % 1 < delta_time:
                damage = 0.005 * self.owner.max_health * int(self.power_stay_counter)
                self.owner.take_damage(damage)

    def _init_effect(self, effect):
        """初始化效果"""
        # 保存原始属性
        if effect.type == BuffType.CHILL:
            self.owner.attack_speed -= 30
        elif effect.type == BuffType.FROZEN:
            self.owner.frozen = True
        elif effect.type == BuffType.INVINCIBLE:
            self.owner.invincible = True
        elif effect.type == BuffType.FIRE:
            self.fire_dmg_counter = 0
        elif effect.type == BuffType.SPEEDUP:
            self.owner.move_speed *= 4
        elif effect.type == BuffType.DIZZY:
            self.owner.dizzy = True
        elif effect.type == BuffType.POWER_STONE:
            self.owner.attack_speed += 50
            self.owner.attack_multiplier *= 2
            self.owner.move_speed *= 1.5
            self.power_stay_counter = 0
            debug_print(f"{self.owner.name}{self.owner.id} 进入了毒圈！")

    def remove(self, effect):
        # 恢复原始属性
        if effect.type == BuffType.CHILL:
            self.owner.attack_speed += 30
        elif effect.type == BuffType.FROZEN:
            self.owner.frozen = False
        elif effect.type == BuffType.INVINCIBLE:
            self.owner.invincible = False
        elif effect.type == BuffType.SPEEDUP:
            self.owner.move_speed /= 4
        elif effect.type == BuffType.DIZZY:
            self.owner.dizzy = False
        elif effect.type == BuffType.POWER_STONE:
            self.owner.attack_speed -= 50
            self.owner.attack_multiplier /= 2
            self.owner.move_speed /= 1.5

class Monster:
    def __init__(self, data, faction, position, battlefield):
        self.name = data["名字"]
        self.faction = faction
        self.position = position
        self.attack_power = data["攻击力"]["数值"]
        self.health = data["生命值"]["数值"]
        self.max_health = self.health
        self.phy_def = data["物理防御"]["数值"]
        self.magic_resist = data["法抗"]["数值"]
        self.attack_interval = data["攻击间隔"]["数值"]
        self.attack_range = data["攻击范围"]["数值"]
        self.move_speed = data["移速"]["数值"]
        self.traits = data["特性"]
        self.attack_type = data["类型"]
        self.char_icon = data.get("符号", "")
        self.id = -1
        self.attack_speed = 100
        # 嘲讽等级
        self.aggro = 0
        
        # 战斗状态
        self.target = None
        self.attack_time_counter = 0
        self.is_alive = True
        self.frozen = False
        self.dizzy = False
        self.invincible = False
        self.battlefield = battlefield
        self.status_system = StatusSystem(self)
        self.element_system = ElementAccumulator(self)
        self.attack_multiplier = 1

    # 新增可扩展的虚方法
    def on_spawn(self):
        """生成时触发的逻辑"""
        pass
    
    def on_death(self):
        """死亡时触发的逻辑"""
        debug_print(f"{self.name}{self.id} 已死亡！")
        pass
    
    def on_hit(self, attacker, damage):
        """被击中时触发的逻辑"""
        pass
    
    def on_attack(self, target, damage):
        """攻击命中时触发的逻辑"""
        pass

    def on_extra_update(self, delta_time):
        """额外更新逻辑"""
        pass

    def increase_skill_cd(self, delta_time):
        """增加技能技力"""
        self.attack_time_counter += delta_time * (np.maximum(10, np.minimum(self.attack_speed, 600)) / 100)
    
    def move_toward_enemy(self, delta_time):
        """根据阵营向对方移动"""
        if self.target and self.target.is_alive:
            # 向目标移动
            direction = self.target.position - self.position

            if np.linalg.norm(direction) <= self.attack_range:
                # 已经在攻击范围内，停止移动
                return
        else:
            return
        
        # 标准化移动向量并应用速度
        norm_direction = direction / np.linalg.norm(direction) if np.any(direction) else direction
        self.position += norm_direction * self.move_speed * delta_time

        # RADIUS = 0.2
        # # 碰撞检测
        # for m in self.battlefield.monsters:
        #     if not m.is_alive or m == self:
        #         continue
        #     dir = m.position - self.position
        #     dist = np.maximum(np.linalg.norm(dir), 0.0001)
        #     dir /= dist
        #     if m != self and dist < RADIUS * 2:
        #         # 发生碰撞，挤出
        #         self.position -= dir * RADIUS
        
        # 限制在场景范围内
        self.position = np.clip(self.position, [0, 0], self.battlefield.map_size)

    def can_attack(self, gameTime):
        return self.attack_time_counter >= self.attack_interval
    
    def update_elemental(self, delta_time):
        if self.element_system.active_burst:
            if self.element_system.active_burst.shouldClearBurst():
                self.element_system.active_burst = None
            else:
                self.element_system.active_burst.update_effect(delta_time)

    def update(self, delta_time):
        if not self.is_alive:
            return
        
        self.on_extra_update(delta_time)
        self.status_system.update(delta_time)
        self.update_elemental(delta_time)

        if self.target is None or not self.target.is_alive:
            # 寻找新目标
            self.target = self.find_target()

        if self.frozen or self.dizzy or not self.is_alive:
            return
        
        self.increase_skill_cd(delta_time)
        # 继续移动
        self.move_toward_enemy(delta_time)
        
        # 优先攻击已有目标
        self.target = self.find_target()
        if self.target and self.target.is_alive:
            if self.can_attack(self.battlefield.gameTime):
                self.attack(self.target, self.battlefield.gameTime)

    def find_target(self):
        """寻找最近的可攻击目标"""
        targets = TargetSelector.select_targets(self, self.battlefield, need_in_range=False, max_targets=1)
        if len(targets) > 0:
            return targets[0]
        return None
    
    def get_attack_power(self):
        return self.attack_multiplier * self.attack_power

    # 攻击相关方法
    def attack(self, target, gameTime):
        direction = target.position - self.position
        distance = np.linalg.norm(direction)

        if distance <= self.attack_range:
            damage = self.calculate_damage(target, self.get_attack_power())
            self.on_attack(target, damage)
            if self.apply_damage_to_target(target, damage):
                target.on_hit(self, damage)
            self.attack_time_counter = 0

    def apply_damage_to_target(self, target, damage) -> bool:
        debug_print(f"{self.name}{self.id} 对 {target.name}{target.id} 造成{damage}点{self.attack_type}伤害")
        if target.take_damage(damage):
            return True
        return False

    def calculate_damage(self, target, damage):
        """计算伤害值"""
        if self.attack_type == "物理":
            return calculate_normal_dmg(target.phy_def, 0, damage, False)
            # return np.maximum(damage - target.phy_def, int(damage * 0.05))
        elif self.attack_type == "魔法":
            return calculate_normal_dmg(target.phy_def, target.magic_resist, damage, True)
            # return int(damage * (1.0 - target.magic_resist / 100))
        
    def take_damage(self, damage) -> bool:
        """承受伤害"""
        if self.invincible:
            return False
        self.health -= damage
        if self.health <= 0:
            self.is_alive = False
            self.on_death()
        return True

class AcidSlug(Monster):
    """酸液源石虫"""
    def apply_damage_to_target(self, target, damage):
        if super().apply_damage_to_target(target, damage):
            # 实现减防特性
            target.phy_def = max(0, target.phy_def - 15)
            debug_print(f"{self.name} 使 {target.name} 防御力降低15")
            return True
        return False

class HighEnergySlug(Monster):
    """高能源石虫"""
    def on_death(self):
        # 实现自爆逻辑
        explosion_radius = 1.25
        debug_print(f"{self.name} 即将自爆！")
        for m in self.battlefield.monsters:
            if m != self and m.faction != self.faction and m.is_alive:
                distance = np.linalg.norm(m.position - self.position)
                if distance <= explosion_radius:
                    dmg = self.calculate_damage(m, self.get_attack_power() * 4)
                    m.take_damage(dmg)
                    debug_print(f"{m.name} 受到{dmg}点爆炸伤害")

class 污染躯壳(Monster):
    """污染躯壳"""
    def on_spawn(self):
        self.speed_boost_counter = 0

    def on_hit(self, attacker, damage):
        super().on_hit(attacker, damage)
        # 触发加速特性
        if self.is_alive and self.speed_boost_counter <= 0:
            speed = BuffEffect(
                    type=BuffType.SPEEDUP,
                    duration=2,
                    source=self
                )
            self.status_system.apply(speed)
            self.speed_boost_counter = 5.0
            debug_print(f"{self.name} 进入极速状态！")

    def on_extra_update(self, delta_time):
        if self.speed_boost_counter > 0:
            self.speed_boost_counter -= delta_time

class 大喷蛛(Monster):
    """大喷蛛"""
    def on_spawn(self):
        self.skill_counter = 0

    def increase_skill_cd(self, delta_time):
        self.skill_counter += delta_time
        if self.skill_counter >= 5:
            self.skill_counter = 0
            self.spawn_small()
        super().increase_skill_cd(delta_time)
    
    def on_death(self):
        self.spawn_small()
        self.spawn_small()
        self.spawn_small()
        self.spawn_small()


    def spawn_small(self):
        debug_print(f"{self.name} 释放小喷蛛")
        self.battlefield.append_monster_name("小喷蛛", self.faction, self.position + np.array([
                        random.uniform(0, 1) * 0.001,
                        random.uniform(0, 1) * 0.001
                    ]))
        
class 鳄鱼(Monster):
    """鳄鱼"""
    def on_attack(self, target, damage):
        # 实现减防特性
        target.phy_def = max(0, target.phy_def - 10)
        debug_print(f"{self.name} 使 {target.name} 防御力降低10")

class 宿主流浪者(Monster):
    """严父"""
    def on_spawn(self):
        self.lastLifeRegenTime = 0
    
    def on_extra_update(self, delta_time):
        if  self.battlefield.gameTime - self.lastLifeRegenTime >= 1.0:
            self.health += 250
            self.health = np.minimum(self.health, self.max_health)
            self.lastLifeRegenTime = self.battlefield.gameTime


class 保鲜膜射手(Monster):
    """保鲜膜射手"""
    def on_spawn(self):
        self.shieldCounter = 30
        self.shieldMode = True
        self.phy_def += 3000
        self.magic_resist += 95
    
    def on_extra_update(self, delta_time):
        self.shieldCounter -= delta_time
        if self.shieldMode and self.shieldCounter <= 0:
            self.phy_def -= 3000
            self.magic_resist -= 95
            self.shieldMode = False
            debug_print(f"{self.name} 保鲜膜失效")

class 狂暴宿主组长(Monster):
    """1750"""
    def on_spawn(self):
        self.lastHurtTime = 0

    def on_extra_update(self, delta_time):
        if self.battlefield.gameTime - self.lastHurtTime >= 1.0:
            self.health -= 500
            self.lastHurtTime = self.battlefield.gameTime
            if self.health <= 0:
                self.is_alive = False
                self.on_death()
            
        
class 海螺(Monster):
    """固海凿石者"""
    def on_spawn(self):
        self.defenseMode = False
        self.last_attack_time = -1
        self.original_speed = self.move_speed

    def on_attack(self, target, damage):
        # 首次攻击
        if self.last_attack_time == -1:
            self.phy_def += 300
            self.defenseMode = True
            self.move_speed = 0
            self.last_attack_time = self.battlefield.gameTime
            debug_print(f"{self.name} 进入防御模式")

    def on_extra_update(self, delta_time):
        if self.defenseMode and self.battlefield.gameTime - self.last_attack_time >= 20.0:
            self.phy_def -= 300
            self.move_speed = self.original_speed
            self.defenseMode = False
            debug_print(f"{self.name} 退出防御模式")


class 拳击囚犯(Monster):
    """拳击囚犯"""
    def on_spawn(self):
        self.attack_speed -= 50
        self.attack_count = 0

    def on_attack(self, target, damage):
        self.attack_count += 1
        if self.attack_count == 4:
            self.attack_speed += 50
            self.attack_power += self.attack_power * 0.5
            debug_print(f"{self.name}{self.id} 已经解放")

    def calculate_damage(self, target, damage):
        """计算伤害值"""
        target_def = target.phy_def
        if self.attack_count >= 4:
            target_def = target_def * 0.4
        return np.maximum(damage - target_def, damage * 0.05)



class 高塔术师(Monster):
    """我们塔神"""
    def on_spawn(self):
        self.lastHurtTime = 0

    def attack(self, target, gameTime):
        targets = TargetSelector.select_targets(self, self.battlefield, need_in_range=True, max_targets=2)
        if len(targets) == 0:
            return
        
        for t in targets:
            for m in self.get_aoe_targets(t):
                damage = self.calculate_damage(m, self.get_attack_power())
                if self.apply_damage_to_target(m, damage):
                    m.on_hit(self, damage)
                    debug_print(f"{self.name}{self.id} 对 {m.name}{m.id} 造成{damage}点{self.attack_type}伤害")

        self.attack_time_counter = 0

    def get_aoe_targets(self, target):
        x, y = self.battlefield.get_grid(target)
        aoe_targets = [m for m in self.battlefield.monsters 
                 if m.is_alive and m.faction != self.faction
                 and abs(self.battlefield.get_grid(m)[0] - x) <= 1 
                 and abs(self.battlefield.get_grid(m)[1] - y) <= 1]
        return aoe_targets

class 冰原术师(Monster):
    """冰手手"""
    def on_spawn(self):
        self.attack_count = 0
        self.targets = []

    def on_attack(self, target, damage):
        self.attack_count += 1
    
    def apply_damage_to_target(self, target, damage):
        # 如果受到伤害施加buff
        if target.take_damage(damage):
            if self.attack_count % 3 == 0:
                # 施加寒冷效果
                chill = BuffEffect(
                    type=BuffType.CHILL,
                    duration=5,
                    source=self
                )
                target.status_system.apply(chill)
            return True
        return False
    
    def attack(self, target, gameTime):
        targets = TargetSelector.select_targets(self, self.battlefield, need_in_range=True, max_targets=2)
        if len(targets) == 0:
            return
        
        for m in targets:
            damage = self.calculate_damage(m, self.get_attack_power())
            if self.apply_damage_to_target(m, damage):
                m.on_hit(self, damage)
        self.attack_time_counter = 0

class 矿脉守卫(Monster):
    """反伤怪"""
    def on_spawn(self):
        self.aggro = 1

    def on_hit(self, attacker, damage):
        if attacker == None:
            return
        damage = self.calculate_damage(attacker, 300)
        if self.apply_damage_to_target(attacker, damage):
            attacker.on_hit(self, damage)
            debug_print(f"{self.name}{self.id} 对 {attacker.name}{attacker.id} 造成{damage}伤害")



class 庞贝(Monster):
    """庞氏骗局"""
    def on_spawn(self):
        self.rage_mode = False
        self.ring_attack_counter = 0

    def attack(self, target, gameTime):
        targets : list[Monster] = TargetSelector.select_targets(self, self.battlefield, need_in_range=True, max_targets=4)
        if len(targets) == 0:
            return
        
        for m in targets:
            damage = self.calculate_damage(m, self.get_attack_power())
            if self.apply_damage_to_target(m, damage):
                m.on_hit(self, damage)
                m.status_system.apply(BuffEffect(
                    type=BuffType.FIRE,
                    duration=10,
                    source=self
                ))
        self.attack_time_counter = 0

    def increase_skill_cd(self, delta_time):
        super().increase_skill_cd(delta_time)

    def on_extra_update(self, delta_time):
        if not self.rage_mode and self.health < 0.5 * self.max_health:
            self.rage_mode = True
            self.attack_speed += 40
            debug_print(f"{self.name} 进入狂暴模式")
            
        targets = TargetSelector.select_targets(self, self.battlefield, need_in_range=False, max_targets=1)
        if len(targets) > 0 and np.linalg.norm(targets[0].position - self.position) < 0.8:
            self.ring_attack_counter += delta_time
            if self.ring_attack_counter >= 10.0:
                targets = TargetSelector.select_targets(self, self.battlefield, need_in_range=False, max_targets=9999)
                targets = [t for t in targets if np.linalg.norm(t.position - self.position) < 1.4]
                for tar in targets:
                    dmg = self.calculate_damage(tar, 1000)
                    if self.apply_damage_to_target(tar, dmg):
                        tar.on_hit(self, dmg)
                self.ring_attack_counter = 0

class 食腐狗(Monster):
    """食腐狗"""
    def on_attack(self, target, damage):
        target.status_system.apply(BuffEffect(
                    type=BuffType.CORRUPT,
                    duration=10,
                    source=self
                ))

class 鼠鼠(Monster):
    """鼠鼠"""
    def on_spawn(self):
        self.speed_boost_counter = 0

    def on_hit(self, attacker, damage):
        super().on_hit(attacker, damage)
        # 触发加速特性
        if self.is_alive and self.speed_boost_counter <= 0:
            speed = BuffEffect(
                    type=BuffType.SPEEDUP,
                    duration=5,
                    source=self
                )
            self.status_system.apply(speed)
            self.speed_boost_counter = 10.0
            debug_print(f"{self.name}{self.id} 进入极速状态！")

    def on_extra_update(self, delta_time):
        if self.speed_boost_counter > 0:
            self.speed_boost_counter -= delta_time

class 雪球(Monster):
    """恐怖雪球投掷手"""
    def on_spawn(self):
        self.first_attack = True

    def attack(self, target, gameTime):
        if not self.first_attack:
            super().attack(target, gameTime)
        else:
            targets : list[Monster] = TargetSelector.select_targets(self, self.battlefield, need_in_range=True, max_targets=1)
            if len(targets) == 0:
                return
            
            self.attack_type = "魔法"
            for m in self.get_aoe_targets(targets[0]):
                damage = self.calculate_damage(m, self.get_attack_power() * 1.5)
                if self.apply_damage_to_target(m, damage):
                    m.on_hit(self, damage)
            self.attack_type = "物理"
            self.attack_range = 0.8
            self.first_attack = False
            debug_print(f"{self.name}{self.id} 投掷雪球")
    
    def get_aoe_targets(self, target):
        x, y = self.battlefield.get_grid(target)
        aoe_targets = [m for m in self.battlefield.monsters 
                if m.is_alive and m.faction != self.faction
                and abs(self.battlefield.get_grid(m)[0] - x) + abs(self.battlefield.get_grid(m)[1] - y) <= 1]
        return aoe_targets

class 船长(Monster):
    """船长"""
    def on_spawn(self):
        self.attack_count = 0

    def on_attack(self, target, damage):
        self.attack_count += 1

    def apply_damage_to_target(self, target, damage):
        if target.take_damage(damage):
            # 每第四下攻击会眩晕对面7秒
            if self.attack_count % 4 == 0:
                chill = BuffEffect(
                    type=BuffType.DIZZY,
                    duration=7,
                    source=self
                )
                target.status_system.apply(chill)
            return True
        return False


class 杰斯顿(Monster):
    """洁厕灵"""
    def on_spawn(self):
        self.rage_mode = False
        self.attack_count = 0
        self.magic_resist += 50
        
    def on_attack(self, target, damage):
        self.attack_count += 1

    def attack(self, target, gameTime):
        if not self.rage_mode:
            if self.attack_count % 4 == 0:
                targets : list[Monster] = TargetSelector.select_targets(self, self.battlefield, need_in_range=True, max_targets=2)
                if len(targets) == 0:
                    return
                # 对两个目标进行攻击，并且带3秒眩晕
                for m in targets:
                    damage = self.calculate_damage(m, self.get_attack_power())
                    if self.apply_damage_to_target(m, damage):
                        m.on_hit(self, damage)
                        m.status_system.apply(BuffEffect(
                            type=BuffType.DIZZY,
                            duration=3,
                            source=self
                        ))
                self.attack_time_counter = 0
            else:
                super().attack(target, gameTime)
                return
        else:
            super().attack(target, gameTime)
            if self.attack_count % 4 == 0:
                super().attack(target, gameTime)
            



    def calculate_damage(self, target : Monster, damage):
        if self.rage_mode and self.attack_count % 4 == 0:
            target_def = target.phy_def * 0.4
            return np.maximum(damage - target_def, damage * 0.05)
        return super().calculate_damage(target, damage)

    def on_death(self):
        if not self.rage_mode:
            switch_stage = BuffEffect(
                type=BuffType.INVINCIBLE,
                duration=4,
                source=self
            )
            dizzy = BuffEffect(
                type=BuffType.DIZZY,
                duration=4,
                source=self
            )
            # 转阶段
            self.status_system.apply(switch_stage)
            self.status_system.apply(dizzy)
            self.rage_mode = True
            self.magic_resist -= 50
            self.attack_type = "物理"
            self.attack_power += 700
            self.phy_def += 1000   
            self.attack_interval -= 1.5
            self.move_speed += 0.3
            self.attack_range = 0.8
            self.attack_count = 0

            self.is_alive = True
            self.health = self.max_health
            print(f"{self.name}{self.id}已进入狂暴状态")
        else:
            super().on_death()

class 镜神(Monster):
    """山海众司魅人"""
    def on_spawn(self):
        # 技力
        self.skill_counter = 25
        self.stage = 0
        self.charging_counter = 0
        self.rage_counter = 0
        self.original_move_speed = self.move_speed
    
    def increase_skill_cd(self, delta_time):
        if self.stage == 0:
            self.skill_counter += delta_time
        elif self.stage == 1:
            self.charging_counter += delta_time
        elif self.stage == 2:
            self.rage_counter += delta_time

        if self.stage == 2 and self.rage_counter >= 20:
            self.stage = 0
            self.move_speed = self.original_move_speed
            self.attack_speed -= 100
            self.skill_counter = 0
        super().increase_skill_cd(delta_time)

    def on_attack(self, target, damage):
        # 如果处于默认状态，释放技能
        if self.stage == 0 and self.skill_counter >= 35:
            self.stage = 1
            self.move_speed = 0
            self.charging_counter = 0
            debug_print(f"{self.name}{self.id} 开始蓄力")
    
    def attack(self, target, gameTime):
        if self.stage == 1:
            # 蓄力5秒后造成攻击力200%法术伤害
            if self.charging_counter >= 5:
                self.stage = 2
                self.move_speed = self.original_move_speed
                self.attack_speed += 100
                self.charging_counter = 0
                self.rage_counter = 0

                damage = self.calculate_damage(target, self.get_attack_power() * 2)
                self.on_attack(target, damage)
                if self.apply_damage_to_target(target, damage):
                    target.on_hit(self, damage)
                self.attack_time_counter = 0
            return
        else:
            super().attack(target, gameTime)

class Vvan(Monster):
    """薇薇安娜"""
    def on_spawn(self):
        # 技力
        self.skill_counter = 20
        self.stage = 0
        self.charging_counter = 0
        self.original_move_speed = self.move_speed
        self.target_pos = None
    
    def increase_skill_cd(self, delta_time):
        if self.stage == 0:
            self.skill_counter += delta_time
        elif self.stage == 1:
            self.charging_counter += delta_time
        super().increase_skill_cd(delta_time)

    def on_extra_update(self, delta_time):
        # 如果处于默认状态，释放技能
        if self.stage == 0 and self.skill_counter >= 25:
            self.target = self.find_target()
            if self.target and self.target.is_alive:
                self.stage = 1
                self.move_speed = 0
                self.charging_counter = 0
                self.target_pos = self.target.position
                debug_print(f"{self.name}{self.id} 开始蓄力")

    def attack(self, target, gameTime):
        if self.stage == 1:
            # 蓄力7秒后造成攻击力250%法术伤害
            if self.charging_counter >= 7:
                self.stage = 0
                self.move_speed = self.original_move_speed
                self.skill_counter = 0
                self.charging_counter = 0

                for m in self.battlefield.monsters:
                    if m.faction != self.faction and m.is_alive:
                        distance = np.linalg.norm(self.target_pos - m.position) #manhatton_distance(self.target_pos, m.position)
                        if distance <= 3.2:
                            dmg = self.calculate_damage(m, self.get_attack_power() * 2.5)
                            if self.apply_damage_to_target(m, dmg):
                                target.on_hit(self, dmg)
                                debug_print(f"{m.name}{m.id} 受到 {self.name}{self.id} 的{dmg}点微光之触伤害")

                self.attack_time_counter = 0
            return
        else:
            super().attack(target, gameTime)



class 萨克斯(Monster):
    """吹笛人"""
    def on_spawn(self):
        # 技力
        self.skill_counter = 10
        self.stage = 0
        self.charging_counter = 0
        self.original_move_speed = self.move_speed
    
    def increase_skill_cd(self, delta_time):
        if self.stage == 0:
            self.skill_counter += delta_time
        elif self.stage == 1:
            self.charging_counter += delta_time
        
        super().increase_skill_cd(delta_time)

    def on_attack(self, target : Monster, damage):
        # 如果处于默认状态，释放技能
        if self.stage == 0 and self.skill_counter >= 20:
            self.stage = 1
            self.move_speed = 0
            self.charging_counter = 0
            self.target_pos = target.position
            debug_print(f"{self.name}{self.id} 开始蓄力")
    
    def attack(self, target, gameTime):
        if self.stage == 1:
            # 蓄力5秒后造成攻击力150%物理伤害
            if self.charging_counter >= 5:
                self.stage = 0
                self.move_speed = self.original_move_speed
                self.skill_counter = 0
                self.charging_counter = 0

                for m in self.get_hit_enemies():
                    dmg = self.calculate_damage(m, self.get_attack_power() * 1.5)
                    if self.apply_damage_to_target(m, dmg):
                        target.on_hit(self, dmg)
                        debug_print(f"{m.name} 受到{dmg}点萨克斯伤害")

                self.attack_time_counter = 0
            return
        else:
            super().attack(target, gameTime)

    def get_hit_enemies(self):
        # 使用整数坐标进行快速分类
        self_x = int(self.position[0])
        self_y = int(self.position[1])
        
        
        smallest_up = 100
        smallest_up_target = None

        smallest_down = 100
        smallest_down_target = None

        smallest_left = 100
        smallest_left_target = None

        smallest_right = 100
        smallest_right_target = None
        # 预处理战场数据
        for m in self.battlefield.monsters:
            if m.faction == self.faction or not m.is_alive:
                continue
            
            # 转换为整数坐标（优化距离计算效率）
            x = int(m.position[0])
            y = int(m.position[1])
            
            # 列坐标匹配（同一垂直方向）
            if x == self_x:
                if m.position[1] > self.position[1] and m.position[1] - self.position[1] < smallest_up:
                    smallest_up = m.position[1] - self.position[1]
                    smallest_up_target = m
                if m.position[1] < self.position[1] and self.position[1] - m.position[1] < smallest_down:
                    smallest_down = self.position[1] - m.position[1]
                    smallest_down_target = m
            
            # 行坐标匹配（同一水平方向）
            if y == self_y:
                if m.position[0] > self.position[0] and m.position[0] - self.position[0] < smallest_right:
                    smallest_right = m.position[0] - self.position[0]
                    smallest_right_target = m
                if m.position[0] < self.position[0] and self.position[0] -m.position[0] < smallest_left:
                    smallest_left = self.position[0] - m.position[0]
                    smallest_left_target = m
        
        targets = []
        if smallest_up_target != None:
            targets.append(smallest_up_target)
        if smallest_down_target != None:
            targets.append(smallest_down_target)
        if smallest_left_target != None:
            targets.append(smallest_left_target)
        if smallest_right_target != None:
            targets.append(smallest_right_target)
        # 返回最近的敌人列表
        return targets
    
class 大君之赐(Monster):
    """大君之赐"""
    def take_damage(self, damage) -> bool:
        """承受伤害"""
        if self.invincible:
            return False
        self.health -= damage * 0.1 + 0.5
        if self.health <= 0:
            self.is_alive = False
            self.on_death()
        return True

class 萨卡兹链术师(Monster):
    """萨卡兹链术师"""

    class AttackNode:
        """攻击节点数据类"""
        __slots__ = ['target', 'damage_multiplier']  # 优化内存使用
        
        def __init__(self, target, multiplier):
            self.target = target
            self.damage_multiplier = multiplier

    def chain_attack(self, initial_target: Monster) -> list[AttackNode]:
        """
        执行连锁攻击
        :param initial_target: 初始攻击目标
        :param battlefield: 战场实例
        :return: 攻击节点列表（包含目标和伤害倍率）
        """
        attack_chain = []
        visited = set()  # 已攻击目标ID缓存
        current_target = initial_target
        current_multiplier = 1.0
        
        # 添加初始攻击
        attack_chain.append(self.AttackNode(current_target, current_multiplier))
        visited.add(current_target.id)

        # 执行最多4次跳跃
        for _ in range(3):
            # 寻找下一个候选目标
            candidates = self._find_candidates(
                current_target.position,
                [m for m in self.battlefield.monsters if m.is_alive and m.faction != self.faction],
                visited
            )
            
            if not candidates:
                break  # 没有可跳跃目标
            
            # 选择最近的目标
            next_target = min(candidates, key=lambda x: x[1])
            current_target = next_target[0]
            current_multiplier *= 0.85
            
            # 记录攻击节点
            attack_chain.append(
                self.AttackNode(current_target, current_multiplier)
            )
            visited.add(current_target.id)
        
        return attack_chain
        

    def _find_candidates(self, 
                        origin: tuple, 
                        enemies: List['Monster'], 
                        visited: set) -> List[tuple]:
        """
        查找有效候选目标
        :param origin: 当前攻击源点坐标 (x, y)
        :param enemies: 可用敌人列表
        :param visited: 已攻击目标ID集合
        :return: 候选列表 (目标, 距离)
        """
        candidates = []
        ox, oy = origin
        
        for enemy in enemies:
            # 排除已攻击目标
            if enemy.id in visited:
                continue
            
            # 计算欧氏距离
            dx = enemy.position[0] - ox
            dy = enemy.position[1] - oy
            distance = math.hypot(dx, dy)
            
            if distance <= 1.6:
                candidates.append( (enemy, distance) )
        
        return candidates

    def attack(self, target, gameTime):
        direction = target.position - self.position
        distance = np.linalg.norm(direction)
            
        if distance <= self.attack_range:
            taragets = self.chain_attack(target)
            for node in taragets:
                base_dmg = self.get_attack_power() * node.damage_multiplier
                dmg = self.calculate_damage(node.target, base_dmg)
                if self.apply_damage_to_target(node.target, dmg):
                    target.on_hit(self, dmg)
                    # 所有人都有一样的凋亡损伤
                    t = ElementType.NECRO_LEFT if self.faction == Faction.LEFT else ElementType.NECRO_RIGHT
                    target.element_system.accumulate(t, self.get_attack_power() * 0.3)
                    # debug_print(f"{self.name}{self.id} 对 {node.target.name}{node.target.id} 造成{dmg}点魔法伤害")
            self.attack_time_counter = 0

    def on_death(self):
        debug_print(f"{self.name} 变成大君之赐")
        self.battlefield.append_monster_name("大君之赐", self.faction, self.position + np.array([
                        random.uniform(-1, 1) * 0.001,
                        random.uniform(-1, 1) * 0.001
                    ]))
        

class MonsterFactory:
    _monster_classes = {
        "酸液源石虫": AcidSlug,
        "高能源石虫": HighEnergySlug,
        "污染躯壳": 污染躯壳,
        "鳄鱼": 鳄鱼,
        "宿主流浪者": 宿主流浪者,
        "保鲜膜": 保鲜膜射手,
        "1750哥": 狂暴宿主组长,
        "海螺": 海螺,
        "拳击囚犯": 拳击囚犯,
        "高塔术师": 高塔术师,
        "冰原术师": 冰原术师,
        "矿脉守卫": 矿脉守卫,
        "庞贝": 庞贝,
        "食腐狗": 食腐狗,
        "鼠鼠": 鼠鼠,
        "雪球": 雪球,
        "船长": 船长,
        "杰斯顿": 杰斯顿,
        "镜神": 镜神,
        "Vvan": Vvan,
        "萨克斯": 萨克斯,
        "大喷蛛": 大喷蛛,
        "萨卡兹链术师":萨卡兹链术师,
        "大君之赐": 大君之赐

        # 添加更多映射...
    }
    
    @classmethod
    def create_monster(cls, data, faction, position, battlefield):
        monster_type = data["名字"]
        if monster_type in cls._monster_classes:
            m = cls._monster_classes[monster_type](data, faction, position, battlefield)
            m.on_spawn()
            return m
        else:
            return Monster(data, faction, position, battlefield)  # 默认类型
