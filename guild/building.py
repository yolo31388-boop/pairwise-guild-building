"""帮派建筑与建设系统"""
from dataclasses import dataclass, field

# 每类建筑的基础建造时间（秒）与升级资源系数
BUILDING_TYPES = {
    "bank":     {"base_time": 120.0, "gold": 200, "wood": 100, "unique": True},
    "barracks": {"base_time": 90.0,  "gold": 150, "wood": 150, "unique": False},
    "wall":     {"base_time": 60.0,  "gold": 100, "wood": 200, "unique": False},
}
DEFAULT_TYPE = {"base_time": 60.0, "gold": 100, "wood": 100, "unique": False}

DEMOLISH_REFUND_RATIO = 0.5   # 拆除返还比例
DEMOLISH_COOLDOWN = 300.0     # 拆除冷却（秒）
REPAIR_COST_PER_POINT = {"gold": 2, "wood": 1}  # 每点耐久维修成本


@dataclass
class Building:
    bid: str
    name: str
    level: int = 1
    max_level: int = 10
    durability: float = 100
    max_durability: float = 100
    under_construction: bool = False
    construction_progress: float = 0.0  # 0.0 ~ 1.0，建造进度条
    invested: dict = field(default_factory=lambda: {"gold": 0, "wood": 0})
    last_demolish_time: float = -1e18   # 上次拆除时间（冷却用）


class BuildingSystem:
    # bug5: 确定的升级优先级（越靠前越优先）
    priority_order = ["bank", "barracks", "wall"]

    def __init__(self):
        self.buildings: dict[str, Building] = {}
        self.guild_level: int = 1
        self.resources: dict = {"gold": 1000, "wood": 500}
        self.now: float = 0.0  # 系统时钟，用于建造/冷却计时

    # ---------- 内部工具 ----------
    def _type_cfg(self, name: str) -> dict:
        return BUILDING_TYPES.get(name, DEFAULT_TYPE)

    def _upgrade_cost(self, building: Building) -> dict:
        """bug1: 升级消耗资金+材料，随等级递增"""
        cfg = self._type_cfg(building.name)
        return {
            "gold": cfg["gold"] * building.level,
            "wood": cfg["wood"] * building.level,
        }

    def _can_afford(self, cost: dict) -> bool:
        return all(self.resources.get(k, 0) >= v for k, v in cost.items())

    def _pay(self, cost: dict) -> None:
        for k, v in cost.items():
            self.resources[k] = self.resources.get(k, 0) - v

    # ---------- bug1: 升级消耗资源+时间 ----------
    def upgrade_building(self, bid: str) -> tuple[bool, str]:
        b = self.buildings.get(bid)
        if b is None:
            return False, "building not found"
        if b.level >= b.max_level:
            return False, "already max level"
        if b.under_construction:
            return False, "under construction"
        if not self.can_build_high_level(b.level + 1):  # bug7 联动
            return False, "guild level too low"
        cost = self._upgrade_cost(b)
        if not self._can_afford(cost):
            return False, "insufficient resources"
        self._pay(cost)
        for k, v in cost.items():
            b.invested[k] = b.invested.get(k, 0) + v
        # 升级需要时间：进入建造状态，完成后才生效
        b.under_construction = True
        b.construction_progress = 0.0
        b.level += 1
        return True, "upgrading"

    def tick(self, seconds: float) -> None:
        """推进系统时钟，建造/升级按进度条推进"""
        self.now += seconds
        for b in self.buildings.values():
            if b.under_construction:
                need = self.get_build_time(b.level)
                b.construction_progress = min(1.0, b.construction_progress + seconds / need)
                if b.construction_progress >= 1.0:
                    b.under_construction = False

    # ---------- bug2: 建造完成后效果才生效 ----------
    def is_effect_active(self, bid: str) -> bool:
        b = self.buildings.get(bid)
        if b is None:
            return False
        return not b.under_construction and b.durability > 0

    # ---------- bug3: 数量上限按帮派等级，特定建筑唯一 ----------
    def get_building_limit(self, name: str) -> int:
        cfg = self._type_cfg(name)
        if cfg["unique"]:
            return 1
        return max(1, 1 + self.guild_level // 2)

    # ---------- bug4: 耐久维修机制 ----------
    def repair_building(self, bid: str) -> tuple[bool, str]:
        b = self.buildings.get(bid)
        if b is None:
            return False, "building not found"
        missing = b.max_durability - b.durability
        if missing <= 0:
            return False, "no damage"
        cost = {
            "gold": int(missing * REPAIR_COST_PER_POINT["gold"]),
            "wood": int(missing * REPAIR_COST_PER_POINT["wood"]),
        }
        if not self._can_afford(cost):
            # 资源不足时尽力部分维修
            affordable_gold = self.resources.get("gold", 0) // REPAIR_COST_PER_POINT["gold"]
            affordable_wood = self.resources.get("wood", 0) // REPAIR_COST_PER_POINT["wood"]
            points = min(missing, affordable_gold, affordable_wood)
            if points <= 0:
                return False, "insufficient resources"
            cost = {
                "gold": int(points * REPAIR_COST_PER_POINT["gold"]),
                "wood": int(points * REPAIR_COST_PER_POINT["wood"]),
            }
        else:
            points = missing
        self._pay(cost)
        b.durability = min(b.max_durability, b.durability + points)
        return True, "repaired"

    # ---------- bug5: 按优先级队列分配 ----------
    def get_upgrade_priority(self, buildings: list) -> str:
        for name in self.priority_order:
            if name in buildings:
                return name
        return sorted(buildings)[0] if buildings else ""

    # ---------- bug6: 建造时间随等级和类型递增 ----------
    def get_build_time(self, level: int, name: str = "") -> float:
        base = self._type_cfg(name)["base_time"]
        return base * level

    # ---------- bug7: 帮派等级是建筑等级前置 ----------
    def can_build_high_level(self, building_level: int) -> bool:
        return building_level <= self.guild_level

    # ---------- bug8: 拆除按比例返还+冷却 ----------
    def demolish_refund(self, bid: str) -> dict:
        b = self.buildings.get(bid)
        if b is None:
            return {}
        if self.now - b.last_demolish_time < DEMOLISH_COOLDOWN:
            return {}
        invested = dict(b.invested)
        if not any(invested.values()):
            # 无投入记录时按等级估算累计建造成本
            cfg = self._type_cfg(b.name)
            invested = {
                "gold": cfg["gold"] * b.level * (b.level - 1) // 2,
                "wood": cfg["wood"] * b.level * (b.level - 1) // 2,
            }
        refund = {
            k: int(v * DEMOLISH_REFUND_RATIO)
            for k, v in invested.items() if v > 0
        }
        for k, v in refund.items():
            self.resources[k] = self.resources.get(k, 0) + v
        b.last_demolish_time = self.now
        del self.buildings[bid]
        return refund
