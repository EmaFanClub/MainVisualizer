"""
分析器基类

定义所有分析器的抽象接口和通用行为。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
from pathlib import Path

if TYPE_CHECKING:
    from PIL import Image
    from src.ingest.manictime.models import ActivityEvent


@dataclass
class AnalyzerResult:
    """
    分析器结果

    Attributes:
        analyzer_name: 分析器名称
        score: 评分 (0.0 - 1.0)
        confidence: 置信度 (0.0 - 1.0)
        reason: 评分原因说明
        details: 详细分析数据
        should_delay: 是否建议延迟处理
        delay_seconds: 建议延迟时间(秒)
    """
    analyzer_name: str
    score: float
    confidence: float = 1.0
    reason: str = ""
    details: dict = field(default_factory=dict)
    should_delay: bool = False
    delay_seconds: int = 0

    def __post_init__(self) -> None:
        """验证并规范化数据"""
        self.score = max(0.0, min(1.0, self.score))
        self.confidence = max(0.0, min(1.0, self.confidence))

    @classmethod
    def zero(cls, analyzer_name: str, reason: str = "无匹配") -> AnalyzerResult:
        """创建零分结果"""
        return cls(
            analyzer_name=analyzer_name,
            score=0.0,
            confidence=1.0,
            reason=reason,
        )

    @classmethod
    def high(
        cls,
        analyzer_name: str,
        reason: str,
        score: float = 0.9,
    ) -> AnalyzerResult:
        """创建高分结果"""
        return cls(
            analyzer_name=analyzer_name,
            score=score,
            confidence=1.0,
            reason=reason,
        )


class BaseAnalyzer(ABC):
    """
    分析器抽象基类

    所有 Stage 2 分析器必须继承此类
    """

    def __init__(
        self,
        name: str,
        weight: float = 1.0,
        enabled: bool = True,
    ) -> None:
        """
        初始化分析器

        Args:
            name: 分析器名称
            weight: 权重 (0.0 - 1.0)
            enabled: 是否启用
        """
        self._name = name
        self._weight = max(0.0, min(1.0, weight))
        self._enabled = enabled
        self._stats = {
            "total_analyzed": 0,
            "total_score": 0.0,
        }

    @property
    def name(self) -> str:
        """分析器名称"""
        return self._name

    @property
    def weight(self) -> float:
        """权重"""
        return self._weight

    @weight.setter
    def weight(self, value: float) -> None:
        """设置权重"""
        self._weight = max(0.0, min(1.0, value))

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
        avg_score = 0.0
        if self._stats["total_analyzed"] > 0:
            avg_score = self._stats["total_score"] / self._stats["total_analyzed"]
        return {
            **self._stats,
            "avg_score": avg_score,
        }

    def analyze(
        self,
        activity: ActivityEvent,
        screenshot: Optional[Image.Image] = None,
    ) -> AnalyzerResult:
        """
        分析活动事件

        Args:
            activity: 活动事件
            screenshot: 关联截图(可选)

        Returns:
            AnalyzerResult: 分析结果
        """
        if not self._enabled:
            return AnalyzerResult.zero(self._name, "分析器已禁用")

        result = self._do_analyze(activity, screenshot)

        # 更新统计
        self._stats["total_analyzed"] += 1
        self._stats["total_score"] += result.score

        return result

    @abstractmethod
    def _do_analyze(
        self,
        activity: ActivityEvent,
        screenshot: Optional[Image.Image] = None,
    ) -> AnalyzerResult:
        """
        执行实际的分析

        子类必须实现此方法

        Args:
            activity: 活动事件
            screenshot: 关联截图(可选)

        Returns:
            AnalyzerResult: 分析结果
        """
        raise NotImplementedError

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "total_analyzed": 0,
            "total_score": 0.0,
        }
