"""
过滤器基类

定义所有过滤器的抽象接口和通用行为。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.ingest.manictime.models import ActivityEvent


@dataclass
class FilterResult:
    """
    过滤器结果

    Attributes:
        should_skip: 是否应跳过该活动
        filter_name: 过滤器名称
        reason: 过滤原因说明
        matched_rule: 匹配的规则(如有)
    """
    should_skip: bool
    filter_name: str
    reason: str = ""
    matched_rule: str = ""

    @classmethod
    def passed(cls, filter_name: str) -> FilterResult:
        """创建通过结果"""
        return cls(
            should_skip=False,
            filter_name=filter_name,
            reason="通过过滤",
        )

    @classmethod
    def skipped(
        cls,
        filter_name: str,
        reason: str,
        matched_rule: str = "",
    ) -> FilterResult:
        """创建跳过结果"""
        return cls(
            should_skip=True,
            filter_name=filter_name,
            reason=reason,
            matched_rule=matched_rule,
        )


class BaseFilter(ABC):
    """
    过滤器抽象基类

    所有 Stage 1 过滤器必须继承此类
    """

    def __init__(self, name: str, enabled: bool = True) -> None:
        """
        初始化过滤器

        Args:
            name: 过滤器名称
            enabled: 是否启用
        """
        self._name = name
        self._enabled = enabled
        self._stats = {
            "total_checked": 0,
            "total_skipped": 0,
        }

    @property
    def name(self) -> str:
        """过滤器名称"""
        return self._name

    @property
    def enabled(self) -> bool:
        """是否启用"""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """设置启用状态"""
        self._enabled = value

    @property
    def stats(self) -> dict:
        """获取统计信息"""
        return self._stats.copy()

    def check(self, activity: ActivityEvent) -> FilterResult:
        """
        检查活动是否应被过滤

        Args:
            activity: 活动事件

        Returns:
            FilterResult: 过滤结果
        """
        if not self._enabled:
            return FilterResult.passed(self._name)

        self._stats["total_checked"] += 1
        result = self._do_check(activity)

        if result.should_skip:
            self._stats["total_skipped"] += 1

        return result

    @abstractmethod
    def _do_check(self, activity: ActivityEvent) -> FilterResult:
        """
        执行实际的过滤检查

        子类必须实现此方法

        Args:
            activity: 活动事件

        Returns:
            FilterResult: 过滤结果
        """
        raise NotImplementedError

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "total_checked": 0,
            "total_skipped": 0,
        }
