"""帮派建筑与建设系统 - 红态测试"""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guild.building import BuildingSystem, Building

class TestUpgradeCost:
    def test_upgrade_requires_resources(self):
        bs = BuildingSystem()
        bs.buildings["b1"] = Building("b1", "bank")
        bs.resources = {"gold": 0, "wood": 0}
        ok, msg = bs.upgrade_building("b1")
        assert ok == False  # bug1: 不消耗也成功

class TestConstructionEffect:
    def test_under_construction_not_active(self):
        bs = BuildingSystem()
        bs.buildings["b1"] = Building("b1", "bank", under_construction=True)
        assert bs.is_effect_active("b1") == False  # bug2: True

class TestBuildingLimit:
    def test_building_has_count_limit(self):
        bs = BuildingSystem()
        assert bs.get_building_limit("bank") < 10  # bug3: 999

class TestRepairMechanism:
    def test_damaged_building_can_be_repaired(self):
        bs = BuildingSystem()
        bs.buildings["b1"] = Building("b1", "bank", durability=10)
        ok, msg = bs.repair_building("b1")
        assert ok == True
        assert bs.buildings["b1"].durability > 10  # bug4: 无变化

class TestUpgradePriority:
    def test_upgrade_priority_not_random(self):
        bs = BuildingSystem()
        buildings = ["bank", "barracks", "wall"]
        # 应该有确定的优先级
        assert hasattr(bs, "priority_order")
        p = bs.get_upgrade_priority(buildings)
        assert p in buildings  # bug5: 随机但至少返回一个

class TestBuildTime:
    def test_higher_level_takes_longer(self):
        bs = BuildingSystem()
        t1 = bs.get_build_time(1)
        t10 = bs.get_build_time(10)
        assert t10 > t1  # bug6: 都是60

class TestGuildLevelRequirement:
    def test_high_level_building_needs_guild_level(self):
        bs = BuildingSystem()
        bs.guild_level = 1
        assert bs.can_build_high_level(10) == False  # bug7: True
        bs.guild_level = 10
        assert bs.can_build_high_level(10) == True

class TestDemolishRefund:
    def test_demolish_returns_resources(self):
        bs = BuildingSystem()
        bs.buildings["b1"] = Building("b1", "bank", level=5)
        refund = bs.demolish_refund("b1")
        assert refund != {}  # bug8: 空
