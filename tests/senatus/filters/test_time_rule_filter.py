"""
TimeRuleFilter 单元测试
"""

from datetime import datetime

import pytest

from src.senatus.filters import TimeRuleFilter, TimeRule


class TestTimeRule:
    """TimeRule 数据类测试"""

    def test_time_rule_creation(self):
        """测试时间规则创建"""
        rule = TimeRule(
            name="work_hours",
            days=[0, 1, 2, 3, 4],
            start_time="09:00",
            end_time="18:00",
            skip_analysis=True,
        )

        assert rule.name == "work_hours"
        assert len(rule.days) == 5
        assert rule.skip_analysis is True
        assert rule.weight_modifier == 1.0

    def test_time_rule_with_modifier(self):
        """测试带权重修改器的规则"""
        rule = TimeRule(
            name="night_high_priority",
            days=[0, 1, 2, 3, 4, 5, 6],
            start_time="22:00",
            end_time="06:00",
            weight_modifier=1.5,
        )

        assert rule.weight_modifier == 1.5


class TestTimeRuleFilter:
    """时间规则过滤器测试"""

    def test_skip_rule_during_active_period(self, make_activity):
        """测试跳过规则在活动时段生效"""
        rule = TimeRule(
            name="skip_lunch",
            days=[5],  # Saturday
            start_time="12:00",
            end_time="14:00",
            skip_analysis=True,
        )
        filter_ = TimeRuleFilter(rules=[rule])

        # 周六 13:00
        activity = make_activity(
            timestamp=datetime(2024, 6, 15, 13, 0, 0)  # Saturday
        )
        result = filter_.check(activity)

        assert result.should_skip is True
        assert "skip_lunch" in result.reason

    def test_no_skip_outside_period(self, make_activity):
        """测试时段外不跳过"""
        rule = TimeRule(
            name="skip_lunch",
            days=[5],  # Saturday
            start_time="12:00",
            end_time="14:00",
            skip_analysis=True,
        )
        filter_ = TimeRuleFilter(rules=[rule])

        # 周六 10:00 (时段外)
        activity = make_activity(
            timestamp=datetime(2024, 6, 15, 10, 0, 0)
        )
        result = filter_.check(activity)

        assert result.should_skip is False

    def test_weight_modifier_rule(self, make_activity):
        """测试权重修改规则"""
        rule = TimeRule(
            name="high_priority_night",
            days=[0, 1, 2, 3, 4, 5, 6],
            start_time="22:00",
            end_time="23:59",
            weight_modifier=1.5,
        )
        filter_ = TimeRuleFilter(rules=[rule])

        activity = make_activity(
            timestamp=datetime(2024, 6, 15, 22, 30, 0)
        )
        result = filter_.check(activity)

        assert result.should_skip is False
        # 权重修改器通过 matched_rule 传递

    def test_overnight_rule(self, make_activity):
        """测试跨夜规则"""
        rule = TimeRule(
            name="overnight",
            days=[5],  # Saturday
            start_time="23:00",
            end_time="02:00",
            skip_analysis=True,
        )
        filter_ = TimeRuleFilter(rules=[rule])

        # 周六 23:30
        activity1 = make_activity(
            timestamp=datetime(2024, 6, 15, 23, 30, 0)
        )
        result1 = filter_.check(activity1)
        assert result1.should_skip is True

    def test_multiple_rules(self, make_activity):
        """测试多规则"""
        rules = [
            TimeRule(
                name="lunch",
                days=[0, 1, 2, 3, 4],
                start_time="12:00",
                end_time="13:00",
                skip_analysis=True,
            ),
            TimeRule(
                name="night",
                days=[0, 1, 2, 3, 4, 5, 6],
                start_time="00:00",
                end_time="06:00",
                weight_modifier=2.0,
            ),
        ]
        filter_ = TimeRuleFilter(rules=rules)

        # 凌晨 3:00
        activity = make_activity(
            timestamp=datetime(2024, 6, 15, 3, 0, 0)
        )
        result = filter_.check(activity)

        # 不跳过，但应用权重修改
        assert result.should_skip is False

    def test_disabled_filter(self, make_activity):
        """测试禁用过滤器"""
        rule = TimeRule(
            name="skip_all",
            days=[0, 1, 2, 3, 4, 5, 6],
            start_time="00:00",
            end_time="23:59",
            skip_analysis=True,
        )
        filter_ = TimeRuleFilter(rules=[rule], enabled=False)

        activity = make_activity()
        result = filter_.check(activity)

        assert result.should_skip is False

    def test_empty_rules(self, make_activity):
        """测试空规则列表"""
        filter_ = TimeRuleFilter(rules=[])

        activity = make_activity()
        result = filter_.check(activity)

        assert result.should_skip is False

    def test_stats_tracking(self, make_activity):
        """测试统计跟踪"""
        rule = TimeRule(
            name="lunch",
            days=[5],  # Saturday
            start_time="12:00",
            end_time="14:00",
            skip_analysis=True,
        )
        filter_ = TimeRuleFilter(rules=[rule])

        # 匹配
        filter_.check(make_activity(timestamp=datetime(2024, 6, 15, 13, 0, 0)))
        # 不匹配
        filter_.check(make_activity(timestamp=datetime(2024, 6, 15, 10, 0, 0)))

        stats = filter_.stats
        assert stats["total_checked"] == 2
        assert stats["total_skipped"] == 1

    def test_filter_name(self):
        """测试过滤器名称"""
        filter_ = TimeRuleFilter()
        assert filter_.name == "time_rule"
