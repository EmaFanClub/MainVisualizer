"""
Senatus 智能触发引擎

整合过滤器、分析器、TI计算器和触发管理器，提供统一的活动处理接口。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from src.core.exceptions import SenatusError
from src.core.logger import get_logger

from .filters import (
    BaseFilter,
    FilterResult,
    WhitelistFilter,
    BlacklistFilter,
    TimeRuleFilter,
    StaticFrameFilter,
)
from .analyzers import BaseAnalyzer, ContextSwitchAnalyzer
from .models import TIResult, TriggerDecision, DecisionType
from .ti_calculator import TabooIndexCalculator
from .trigger_manager import TriggerManager, TriggerThresholds

if TYPE_CHECKING:
    from PIL import Image
    from src.ingest.manictime.models import ActivityEvent
    from src.core.interfaces.vlm_provider import IVLMProvider

logger = get_logger(__name__)


class SenatusEngine:
    """
    Senatus 智能触发引擎

    负责分析活动序列，计算 Taboo Index (ti)，决定是否触发 VLM 深度分析。
    采用三级级联推理架构以最小化 VLM 调用成本。

    级联架构:
        Stage 1: 规则过滤 - 使用过滤器快速排除不需要分析的活动
        Stage 2: 轻量分类 - 使用分析器计算 TI 分数
        Stage 3: 触发决策 - 根据阈值决定 VLM 调用策略

    Attributes:
        filters: Stage 1 过滤器列表
        ti_calculator: TI 计算器(包含 Stage 2 分析器)
        trigger_manager: Stage 3 触发决策管理器
    """

    def __init__(
        self,
        filters: Optional[list[BaseFilter]] = None,
        analyzers: Optional[list[BaseAnalyzer]] = None,
        thresholds: Optional[TriggerThresholds] = None,
        max_batch_size: int = 10,
        batch_timeout_seconds: int = 300,
    ) -> None:
        """
        初始化 Senatus 引擎

        Args:
            filters: 自定义过滤器列表
            analyzers: 自定义分析器列表
            thresholds: 触发阈值配置
            max_batch_size: 最大批处理大小
            batch_timeout_seconds: 批处理超时时间(秒)
        """
        # Stage 1: 过滤器
        self._filters: list[BaseFilter] = filters or []
        if not self._filters:
            self._setup_default_filters()

        # Stage 2: TI 计算器
        self._ti_calculator = TabooIndexCalculator(analyzers=analyzers)

        # Stage 3: 触发管理器
        self._trigger_manager = TriggerManager(
            thresholds=thresholds,
            max_batch_size=max_batch_size,
            batch_timeout_seconds=batch_timeout_seconds,
        )

        # 统计信息
        self._stats = {
            "total_processed": 0,
            "filtered_count": 0,
            "analyzed_count": 0,
        }

        logger.info("Senatus 引擎初始化完成")

    def _setup_default_filters(self) -> None:
        """
        设置默认过滤器

        默认过滤器顺序:
        1. WhitelistFilter - 白名单应用跳过分析
        2. BlacklistFilter - 黑名单应用标记优先处理
        3. TimeRuleFilter - 时间规则过滤
        4. StaticFrameFilter - 静态帧检测跳过重复画面
        """
        self._filters = [
            WhitelistFilter(),
            BlacklistFilter(),
            TimeRuleFilter(),
            StaticFrameFilter(),
        ]

    @property
    def filters(self) -> list[BaseFilter]:
        """获取过滤器列表"""
        return self._filters.copy()

    @property
    def ti_calculator(self) -> TabooIndexCalculator:
        """获取 TI 计算器"""
        return self._ti_calculator

    @property
    def trigger_manager(self) -> TriggerManager:
        """获取触发管理器"""
        return self._trigger_manager

    def add_filter(self, filter_: BaseFilter) -> None:
        """添加过滤器"""
        self._filters.append(filter_)

    def remove_filter(self, name: str) -> bool:
        """移除过滤器"""
        for i, f in enumerate(self._filters):
            if f.name == name:
                self._filters.pop(i)
                return True
        return False

    def process_activity(
        self,
        activity: ActivityEvent,
        screenshot: Optional[Image.Image] = None,
    ) -> TriggerDecision:
        """
        处理单个活动事件

        执行三级级联推理:
        1. Stage 1: 规则过滤 - 过滤白名单/静态帧
        2. Stage 2: 轻量分类 - 计算 TI 和置信度
        3. Stage 3: 触发决策 - 根据阈值决定 VLM 调用

        Args:
            activity: 待处理的活动事件
            screenshot: 关联截图(可选)

        Returns:
            TriggerDecision: 包含触发类型和相关元数据的决策对象

        Raises:
            SenatusError: 处理过程中发生错误时抛出
        """
        self._stats["total_processed"] += 1

        try:
            # Stage 1: 规则过滤
            filter_result = self._apply_filters(activity)
            if filter_result.should_skip:
                self._stats["filtered_count"] += 1
                logger.debug(f"活动被过滤: {activity.event_id}, 原因: {filter_result.reason}")
                return TriggerDecision.create_filtered(
                    event_id=activity.event_id,
                    filter_name=filter_result.filter_name,
                    reason=filter_result.reason,
                )

            # Stage 2: 轻量分类 - 计算 TI
            self._stats["analyzed_count"] += 1
            ti_result = self._ti_calculator.calculate(activity, screenshot)

            # Stage 3: 触发决策
            decision = self._trigger_manager.evaluate(activity, ti_result)

            return decision

        except Exception as e:
            logger.error(f"处理活动失败: {activity.event_id}, 错误: {e}")
            raise SenatusError(
                f"处理活动 {activity.event_id} 失败",
                details={"error": str(e), "activity": str(activity)},
            ) from e

    def process_batch(
        self,
        activities: list[ActivityEvent],
        screenshots: Optional[dict[str, Image.Image]] = None,
    ) -> list[TriggerDecision]:
        """
        批量处理活动事件

        Args:
            activities: 活动事件列表
            screenshots: 截图字典，key 为事件 ID 字符串

        Returns:
            TriggerDecision 列表
        """
        decisions = []
        screenshots = screenshots or {}

        for activity in activities:
            screenshot = screenshots.get(str(activity.event_id))
            decision = self.process_activity(activity, screenshot)
            decisions.append(decision)

        return decisions

    def _apply_filters(self, activity: ActivityEvent) -> FilterResult:
        """
        应用所有过滤器

        Args:
            activity: 活动事件

        Returns:
            FilterResult: 第一个命中的过滤结果，或通过结果
        """
        for filter_ in self._filters:
            result = filter_.check(activity)
            if result.should_skip:
                return result

        return FilterResult.passed("all")

    def check_batch_queue(self) -> list[tuple[ActivityEvent, TIResult]]:
        """
        检查批处理队列

        Returns:
            就绪的活动和 TI 结果列表
        """
        return self._trigger_manager.check_batch_ready()

    def check_delayed_queue(self) -> list[tuple[ActivityEvent, TIResult]]:
        """
        检查延迟队列

        Returns:
            就绪的活动和 TI 结果列表
        """
        return self._trigger_manager.check_delayed_ready()

    def flush_batch_queue(self) -> list[tuple[ActivityEvent, TIResult]]:
        """
        强制刷新批处理队列

        Returns:
            所有队列中的活动和 TI 结果
        """
        return self._trigger_manager.flush_batch_queue()

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            包含各组件统计信息的字典
        """
        filter_stats = {}
        for f in self._filters:
            filter_stats[f.name] = f.stats

        return {
            "engine": self._stats.copy(),
            "filters": filter_stats,
            "ti_calculator": self._ti_calculator.stats,
            "trigger_manager": self._trigger_manager.stats,
        }

    def reset_stats(self) -> None:
        """重置所有统计信息"""
        self._stats = {
            "total_processed": 0,
            "filtered_count": 0,
            "analyzed_count": 0,
        }
        for f in self._filters:
            f.reset_stats()
        self._ti_calculator.reset_stats()
        self._trigger_manager.reset_stats()

    def get_filter_rate(self) -> float:
        """
        获取过滤率

        Returns:
            被过滤的活动比例
        """
        total = self._stats["total_processed"]
        if total == 0:
            return 0.0
        return self._stats["filtered_count"] / total

    def get_trigger_rate(self) -> float:
        """
        获取触发率

        返回需要 VLM 分析的活动比例(IMMEDIATE + BATCH)

        Returns:
            需要分析的活动比例
        """
        total = self._stats["total_processed"]
        if total == 0:
            return 0.0

        trigger_stats = self._trigger_manager.stats
        triggered = trigger_stats["immediate_count"] + trigger_stats["batch_count"]
        return triggered / total

    def get_context_switch_analyzer(self) -> Optional[ContextSwitchAnalyzer]:
        """
        获取上下文切换分析器实例

        用于访问分析器的历史记录和切换模式统计

        Returns:
            ContextSwitchAnalyzer 实例，如果未注册则返回 None
        """
        for analyzer in self._ti_calculator.analyzers:
            if isinstance(analyzer, ContextSwitchAnalyzer):
                return analyzer
        return None

    def set_context_window(self, activities: list[ActivityEvent]) -> None:
        """
        设置上下文切换分析器的历史窗口

        用于从外部注入历史活动序列

        Args:
            activities: 历史活动列表
        """
        analyzer = self.get_context_switch_analyzer()
        if analyzer:
            analyzer.set_context_window(activities)
        else:
            logger.warning("ContextSwitchAnalyzer 未注册，无法设置上下文窗口")

    def get_static_frame_filter(self) -> Optional[StaticFrameFilter]:
        """
        获取静态帧过滤器实例

        用于访问帧哈希历史或调整阈值

        Returns:
            StaticFrameFilter 实例，如果未注册则返回 None
        """
        for filter_ in self._filters:
            if isinstance(filter_, StaticFrameFilter):
                return filter_
        return None
