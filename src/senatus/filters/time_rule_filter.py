"""
时间规则过滤器

基于时间规则调整分析策略，支持按时间段配置不同的处理行为。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import TYPE_CHECKING, Optional

from .base_filter import BaseFilter, FilterResult

if TYPE_CHECKING:
    from src.ingest.manictime.models import ActivityEvent


@dataclass
class TimeRule:
    """
    时间规则定义

    Attributes:
        name: 规则名称
        days: 适用的星期几列表 (0=周一, 6=周日)
        start_time: 开始时间 (HH:MM 格式)
        end_time: 结束时间 (HH:MM 格式)
        skip_analysis: 是否跳过分析
        weight_modifier: 权重修正因子
        reason: 规则说明
    """
    name: str
    days: list[int]
    start_time: str
    end_time: str
    skip_analysis: bool = False
    weight_modifier: float = 1.0
    reason: str = ""

    def __post_init__(self) -> None:
        """验证并解析时间"""
        self._start = self._parse_time(self.start_time)
        self._end = self._parse_time(self.end_time)

        # 验证星期范围
        for day in self.days:
            if day < 0 or day > 6:
                raise ValueError(f"无效的星期值: {day}, 应为 0-6")

    def _parse_time(self, time_str: str) -> time:
        """解析时间字符串"""
        try:
            parts = time_str.split(":")
            return time(hour=int(parts[0]), minute=int(parts[1]))
        except (ValueError, IndexError) as e:
            raise ValueError(f"无效的时间格式: {time_str}, 应为 HH:MM") from e

    def matches(self, dt: datetime) -> bool:
        """
        检查时间是否匹配此规则

        Args:
            dt: 要检查的时间

        Returns:
            是否匹配
        """
        # 检查星期
        weekday = dt.weekday()
        if weekday not in self.days:
            return False

        # 检查时间段
        current_time = dt.time()

        # 处理跨午夜的情况
        if self._start <= self._end:
            # 正常情况: 开始时间 < 结束时间
            return self._start <= current_time <= self._end
        else:
            # 跨午夜: 如 23:00 - 06:00
            return current_time >= self._start or current_time <= self._end


# 默认时间规则
DEFAULT_TIME_RULES = [
    TimeRule(
        name="office_hours",
        days=[0, 1, 2, 3, 4],  # 周一到周五
        start_time="09:00",
        end_time="18:00",
        skip_analysis=False,
        weight_modifier=0.7,
        reason="办公时间，降低敏感度",
    ),
    TimeRule(
        name="lunch_break",
        days=[0, 1, 2, 3, 4],  # 周一到周五
        start_time="12:00",
        end_time="13:00",
        skip_analysis=True,
        weight_modifier=0.5,
        reason="午餐时间，可跳过分析",
    ),
    TimeRule(
        name="late_night",
        days=[0, 1, 2, 3, 4, 5, 6],  # 每天
        start_time="23:00",
        end_time="06:00",
        skip_analysis=False,
        weight_modifier=1.2,
        reason="深夜时段，提高敏感度",
    ),
    TimeRule(
        name="weekend",
        days=[5, 6],  # 周六周日
        start_time="00:00",
        end_time="23:59",
        skip_analysis=False,
        weight_modifier=1.1,
        reason="周末时段",
    ),
]


@dataclass
class TimeRuleMatch:
    """
    时间规则匹配结果

    Attributes:
        matched: 是否匹配到规则
        rule: 匹配的规则(如有)
        weight_modifier: 最终权重修正因子
    """
    matched: bool
    rule: Optional[TimeRule] = None
    weight_modifier: float = 1.0


class TimeRuleFilter(BaseFilter):
    """
    时间规则过滤器

    基于预定义的时间规则调整分析策略。可以配置:
    - 特定时间段跳过分析
    - 特定时间段调整权重

    Attributes:
        rules: 时间规则列表
        skip_on_match: 匹配时是否跳过
    """

    def __init__(
        self,
        rules: Optional[list[TimeRule]] = None,
        use_default_rules: bool = True,
        enabled: bool = True,
    ) -> None:
        """
        初始化时间规则过滤器

        Args:
            rules: 自定义时间规则列表
            use_default_rules: 是否使用默认规则
            enabled: 是否启用
        """
        super().__init__(name="time_rule", enabled=enabled)

        self._rules: list[TimeRule] = []

        # 添加默认规则
        if use_default_rules:
            self._rules.extend(DEFAULT_TIME_RULES)

        # 添加自定义规则
        if rules:
            self._rules.extend(rules)

        # 扩展统计
        self._stats.update({
            "rule_matches": 0,
            "skipped_by_rule": 0,
        })

    def _do_check(self, activity: ActivityEvent) -> FilterResult:
        """
        执行时间规则检查

        Args:
            activity: 活动事件

        Returns:
            FilterResult: 过滤结果
        """
        # 获取活动时间
        activity_time = activity.timestamp

        # 查找匹配的规则
        match = self._find_matching_rule(activity_time)

        if match.matched and match.rule:
            self._stats["rule_matches"] += 1

            rule = match.rule

            if rule.skip_analysis:
                self._stats["skipped_by_rule"] += 1
                return FilterResult.skipped(
                    filter_name=self.name,
                    reason=f"时间规则跳过: {rule.name} - {rule.reason}",
                    matched_rule=f"time:{rule.name}:skip",
                )

            # 不跳过，但在 matched_rule 中提供权重修正信息
            return FilterResult(
                should_skip=False,
                filter_name=self.name,
                reason=f"时间规则应用: {rule.name} - {rule.reason}",
                matched_rule=f"time:{rule.name}:weight={rule.weight_modifier}",
            )

        return FilterResult.passed(self.name)

    def _find_matching_rule(self, dt: datetime) -> TimeRuleMatch:
        """
        查找匹配的时间规则

        优先返回 skip_analysis=True 的规则

        Args:
            dt: 活动时间

        Returns:
            TimeRuleMatch: 匹配结果
        """
        skip_match = None
        normal_match = None

        for rule in self._rules:
            if rule.matches(dt):
                if rule.skip_analysis:
                    skip_match = rule
                elif normal_match is None:
                    normal_match = rule

        # 优先返回跳过规则
        if skip_match:
            return TimeRuleMatch(
                matched=True,
                rule=skip_match,
                weight_modifier=skip_match.weight_modifier,
            )

        if normal_match:
            return TimeRuleMatch(
                matched=True,
                rule=normal_match,
                weight_modifier=normal_match.weight_modifier,
            )

        return TimeRuleMatch(matched=False)

    def get_weight_modifier(self, dt: datetime) -> float:
        """
        获取指定时间的权重修正因子

        Args:
            dt: 时间

        Returns:
            权重修正因子 (1.0 表示无修正)
        """
        match = self._find_matching_rule(dt)
        return match.weight_modifier

    def should_skip(self, dt: datetime) -> bool:
        """
        检查指定时间是否应跳过分析

        Args:
            dt: 时间

        Returns:
            是否应跳过
        """
        match = self._find_matching_rule(dt)
        if match.matched and match.rule:
            return match.rule.skip_analysis
        return False

    def add_rule(self, rule: TimeRule) -> None:
        """添加时间规则"""
        self._rules.append(rule)

    def remove_rule(self, name: str) -> bool:
        """
        移除时间规则

        Args:
            name: 规则名称

        Returns:
            是否成功移除
        """
        for i, rule in enumerate(self._rules):
            if rule.name == name:
                self._rules.pop(i)
                return True
        return False

    def get_rule(self, name: str) -> Optional[TimeRule]:
        """
        获取指定名称的规则

        Args:
            name: 规则名称

        Returns:
            规则对象或 None
        """
        for rule in self._rules:
            if rule.name == name:
                return rule
        return None

    @property
    def rules(self) -> list[TimeRule]:
        """获取所有规则"""
        return self._rules.copy()

    def clear_rules(self) -> None:
        """清除所有规则"""
        self._rules.clear()
