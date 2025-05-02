

from dataclasses import dataclass, field
from enum import Enum


DEBUG = True

def debug_print(msg):
    if DEBUG:
        print(msg)

class Faction(Enum):
    LEFT = 0
    RIGHT = 1

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