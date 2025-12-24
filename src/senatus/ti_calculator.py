"""
Taboo Index (TI) 计算器

负责计算活动的 TI 分数，整合多个分析器的结果。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from src.core.logger import get_logger

from .models import TIResult, TILevel, ComponentScore
from .analyzers import (
    BaseAnalyzer,
    MetadataAnalyzer,
    VisualAnalyzer,
    FrameDiffAnalyzer,
    ContextSwitchAnalyzer,
    UncertaintyAnalyzer,
)

if TYPE_CHECKING:
    from PIL import Image
    from src.ingest.manictime.models import ActivityEvent

logger = get_logger(__name__)


class TabooIndexCalculator:
    """
    Taboo Index 计算器

    整合多个分析器计算最终的 TI 分数

    Attributes:
        analyzers: 分析器列表
        default_confidence: 默认置信度
    """

    def __init__(
        self,
        analyzers: Optional[list[BaseAnalyzer]] = None,
        default_confidence: float = 1.0,
    ) -> None:
        """
        初始化 TI 计算器

        Args:
            analyzers: 自定义分析器列表
            default_confidence: 默认置信度
        """
        self._analyzers: list[BaseAnalyzer] = analyzers or []
        self._default_confidence = default_confidence
        self._stats = {
            "total_calculated": 0,
            "avg_ti_score": 0.0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "minimal_count": 0,
        }

        # 如果没有提供分析器，使用默认配置
        if not self._analyzers:
            self._setup_default_analyzers()

    def _setup_default_analyzers(self) -> None:
        """
        设置默认分析器

        默认分析器及权重:
        1. MetadataAnalyzer - 元数据分析 (权重 0.25)
        2. VisualAnalyzer - 视觉敏感度分析 (权重 0.35, 最高)
        3. ContextSwitchAnalyzer - 上下文切换检测 (权重 0.15)
        4. FrameDiffAnalyzer - 帧差异分析 (权重 0.15)
        5. UncertaintyAnalyzer - 不确定性评估 (权重 0.10, 最低)

        注意: 权重总和为 1.0
        """
        self._analyzers = [
            MetadataAnalyzer(weight=0.25),
            VisualAnalyzer(weight=0.35),
            ContextSwitchAnalyzer(weight=0.15),
            FrameDiffAnalyzer(weight=0.15),
            UncertaintyAnalyzer(weight=0.10),
        ]

    @property
    def analyzers(self) -> list[BaseAnalyzer]:
        """获取分析器列表"""
        return self._analyzers.copy()

    @property
    def stats(self) -> dict:
        """获取统计信息"""
        return self._stats.copy()

    def add_analyzer(self, analyzer: BaseAnalyzer) -> None:
        """添加分析器"""
        self._analyzers.append(analyzer)

    def remove_analyzer(self, name: str) -> bool:
        """移除分析器"""
        for i, analyzer in enumerate(self._analyzers):
            if analyzer.name == name:
                self._analyzers.pop(i)
                return True
        return False

    def calculate(
        self,
        activity: ActivityEvent,
        screenshot: Optional[Image.Image] = None,
    ) -> TIResult:
        """
        计算活动的 TI 分数

        Args:
            activity: 活动事件
            screenshot: 关联截图(可选)

        Returns:
            TIResult: 计算结果
        """
        logger.debug(f"计算活动 TI: {activity.event_id}")

        component_scores: dict[str, ComponentScore] = {}
        should_delay = False
        delay_seconds = 0
        min_confidence = self._default_confidence

        # 运行所有分析器
        for analyzer in self._analyzers:
            if not analyzer.enabled:
                continue

            result = analyzer.analyze(activity, screenshot)

            # 记录组件分数
            component_scores[analyzer.name] = ComponentScore(
                name=analyzer.name,
                score=result.score,
                weight=analyzer.weight,
                weighted_score=result.score * analyzer.weight,
                reason=result.reason,
            )

            # 更新延迟标志
            if result.should_delay:
                should_delay = True
                delay_seconds = max(delay_seconds, result.delay_seconds)

            # 更新最小置信度
            min_confidence = min(min_confidence, result.confidence)

        # 创建 TI 结果
        ti_result = TIResult.create_from_scores(
            event_id=activity.event_id,
            component_scores=component_scores,
            confidence=min_confidence,
            should_delay=should_delay,
            delay_seconds=delay_seconds,
        )

        # 更新统计
        self._update_stats(ti_result)

        logger.debug(
            f"TI 计算完成: score={ti_result.ti_score:.3f}, "
            f"level={ti_result.ti_level.value}"
        )

        return ti_result

    def _update_stats(self, result: TIResult) -> None:
        """更新统计信息"""
        self._stats["total_calculated"] += 1

        # 更新平均分
        total = self._stats["total_calculated"]
        prev_avg = self._stats["avg_ti_score"]
        self._stats["avg_ti_score"] = prev_avg + (result.ti_score - prev_avg) / total

        # 更新级别计数
        if result.ti_level == TILevel.HIGH:
            self._stats["high_count"] += 1
        elif result.ti_level == TILevel.MEDIUM:
            self._stats["medium_count"] += 1
        elif result.ti_level == TILevel.LOW:
            self._stats["low_count"] += 1
        else:
            self._stats["minimal_count"] += 1

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "total_calculated": 0,
            "avg_ti_score": 0.0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "minimal_count": 0,
        }
        for analyzer in self._analyzers:
            analyzer.reset_stats()
