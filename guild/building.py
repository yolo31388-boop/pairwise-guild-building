"""帮派建筑与建设系统"""
import time
from dataclasses import dataclass, field


@dataclass
class Building:
    bid: str
    name: str
    level: int = 1
    max_level: int = 10
    durability: float = 100
    max_durability: float = 100
    under_construction: bool = False
    construction_progress: float = 0.0  # 0.0 ~ 1.0


class BuildingSystem:
    # bug5: 确定的升级优先级（越靠前越优先）
    priority_order: list = ["bank", "barracks", "wall", "warehouse", "altar"]

    # bug3: 唯一建筑，全帮派只能建一个
    UNIQUE_BUILDINGS: set = {"bank", "altar"}

    # bug8: 拆除返还比例与冷却（秒）
    REFUND_RATE: float = 0.5
    DEMOLISH_COOLDOWN: float = 300.0

    BASE_BUILD_TIME: float = 60.0
    # 建筑类型耗时倍率
    TYPE_TIME_MULTIPLIER: dict = {"bank": 2.0, "barracks": 1.5, "wall": 1.0}

    def __init__(self):
        self.buildings: dict[str, Building] = {}
        self.guild_level: int = 1
        self.resources: dict = {"gold": 1000, "wood": 500}
        self._last_demolish_time: float = 0.0

    # ---- bug1: 升级消耗资金+材料+时间 ----
    def get_upgrade_cost(self, target_level: int) -> dict:
        return {"gold": 100 * target_level, "wood": 50 * target_level}

    def upgrade_building(self, bid: str) -> tuple[bool, str]:
        b = self.buildings.get(bid)
        if b is None:
            return False, "building not found"
        if b.under_construction:
            return False, "already under construction"
        if b.level >= b.max_level:
            return False, "max level reached"
        target = b.level + 1
        # bug7: 帮派等级是建筑等级的前置
        if not self.can_build_high_level(target):
            return False, "guild level too low"
        cost = self.get_upgrade_cost(target)
        for res, amount in cost.items():
            if self.resources.get(res, 0) < amount:
                return False, f"not enough {res}"
        for res, amount in cost.items():
            self.resources[res] -= amount
        # 消耗时间：进入建造状态，完工后才生效
        b.level = target
        b.under_construction = True
        b.construction_progress = 0.0
        return True, "upgrading"

    def advance_construction(self, bid: str, elapsed: float) -> float:
        """推进建造进度，返回当前进度（0~1）。"""
        b = self.buildings.get(bid)
        if b is None or not b.under_construction:
            return 1.0
        total = self.get_build_time(b.level, b.name)
        b.construction_progress = min(1.0, b.construction_progress + elapsed / total)
        if b.construction_progress >= 1.0:
            b.under_construction = False
        return b.construction_progress

    # ---- bug2: 建造完成后效果才生效 ----
    def is_effect_active(self, bid: str) -> bool:
        b = self.buildings.get(bid)
        if b is None:
            return False
        return not b.under_construction and b.durability > 0

    # ---- bug3: 数量按帮派等级有上限，特定建筑唯一 ----
    def get_building_limit(self, bid: str) -> int:
        if bid in self.UNIQUE_BUILDINGS:
            return 1
        return 1 + self.guild_level // 2

    # ---- bug4: 耐久度维修机制 ----
    def repair_building(self, bid: str) -> tuple[bool, str]:
        b = self.buildings.get(bid)
        if b is None:
            return False, "building not found"
        missing = b.max_durability - b.durability
        if missing <= 0:
            return False, "durability already full"
        # 每点耐久消耗 1 金币，钱不够就修多少算多少
        affordable = min(missing, float(self.resources.get("gold", 0)))
        if affordable <= 0:
            return False, "not enough gold"
        self.resources["gold"] -= affordable
        b.durability += affordable
        return True, "repaired"

    # ---- bug5: 按优先级队列分配，资源不足时高优先级先升级 ----
    def get_upgrade_priority(self, buildings: list) -> str:
        for name in self.priority_order:
            if name in buildings:
                return name
        return buildings[0] if buildings else ""

    # ---- bug6: 建造时间随等级和类型递增 ----
    def get_build_time(self, level: int, building_type: str = "wall") -> float:
        multiplier = self.TYPE_TIME_MULTIPLIER.get(building_type, 1.0)
        return self.BASE_BUILD_TIME * level * multiplier

    # ---- bug7: 高等级建筑需要高帮派等级 ----
    def can_build_high_level(self, building_level: int) -> bool:
        return building_level <= self.guild_level

    # ---- bug8: 拆除按比例返还资源，有冷却 ----
    def demolish_refund(self, bid: str) -> dict:
        b = self.buildings.get(bid)
        if b is None:
            return {}
        now = time.monotonic()
        if now - self._last_demolish_time < self.DEMOLISH_COOLDOWN:
            return {}
        invested = {"gold": 0, "wood": 0}
        for lvl in range(1, b.level + 1):
            cost = self.get_upgrade_cost(lvl)
            for res, amount in cost.items():
                invested[res] += amount
        refund = {res: int(amount * self.REFUND_RATE) for res, amount in invested.items()}
        for res, amount in refund.items():
            self.resources[res] = self.resources.get(res, 0) + amount
        del self.buildings[bid]
        self._last_demolish_time = now
        return refund
