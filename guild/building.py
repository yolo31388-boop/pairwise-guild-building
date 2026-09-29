"""帮派建筑与建设系统 - 含8个bug"""
from dataclasses import dataclass, field

@dataclass
class Building:
    bid: str
    name: str
    level: int = 1
    max_level: int = 10
    durability: float = 100  # bug4: 无维修
    under_construction: bool = False  # bug2: 建造中也生效

class BuildingSystem:
    def __init__(self):
        self.buildings: dict[str, Building] = {}
        self.guild_level: int = 1
        self.resources: dict = {"gold": 1000, "wood": 500}

    def upgrade_building(self, bid: str) -> tuple[bool, str]:
        # bug1: 不消耗资源
        self.buildings[bid].level += 1
        return True, "upgraded"

    def is_effect_active(self, bid: str) -> bool:
        # bug2: 建造中也生效
        return True

    def get_building_limit(self, bid: str) -> int:
        # bug3: 无数量上限
        return 999

    def repair_building(self, bid: str) -> tuple[bool, str]:
        # bug4: 无维修机制
        return True, "repaired"

    def get_upgrade_priority(self, buildings: list) -> str:
        # bug5: 无优先级随机选
        import random
        return random.choice(buildings)

    def get_build_time(self, level: int) -> float:
        # bug6: 固定时间
        return 60.0

    def can_build_high_level(self, building_level: int) -> bool:
        # bug7: 帮派等级不挂钩
        return True

    def demolish_refund(self, bid: str) -> dict:
        # bug8: 拆除不返还
        return {}
