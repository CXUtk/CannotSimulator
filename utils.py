

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


DEBUG = False

def debug_print(msg):
    if DEBUG:
        print(msg)

class Faction(Enum):
    LEFT = 0
    RIGHT = 1

class DamageType(Enum):
    PHYSICAL = "物理"
    MAGIC = "法术"
    TRUE = "真实"

    def __str__(self):
        return self.value  # 直接返回值字符串

class BuffType(Enum):
    CHILL = 0
    FROZEN = 1
    INVINCIBLE = 2
    FIRE = 3
    CORRUPT = 4
    SPEEDUP = 5
    DIZZY = 6
    POWER_STONE = 7 # 源石地板
    WINE = 8        # 酒桶的效果
    INVINCIBLE2 = 9 # 转阶段无敌，不会被设为目标

class ElementType(Enum):
    NECRO_LEFT = "凋亡左"  # 凋亡元素（原凋亡损伤）
    NECRO_RIGHT = "凋亡右"  # 凋亡元素（原凋亡损伤）
    FIRE = "灼燃"

def lerp(a, b, x):
    return a + (b - a) * x


@dataclass
class BuffEffect:
    type: BuffType
    duration: float
    source: any = None
    stacks: int = 1
    data: dict = field(default_factory=dict)


VIRTUAL_TIME_STEP = 60 # 60帧相当于一秒
VIRTUAL_TIME_DELTA = 1.0 / VIRTUAL_TIME_STEP

def calculate_normal_dmg(defense, magic_resist, dmg, damageType: DamageType):
    """计算伤害值"""
    if damageType == DamageType.PHYSICAL:
        return np.maximum(dmg - defense, dmg * 0.05)
    elif damageType == DamageType.MAGIC:
        return np.maximum(dmg * 0.05, dmg * (1.0 - magic_resist / 100))
    elif damageType == DamageType.TRUE:
        return dmg