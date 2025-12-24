"""
触发管理器

负责根据 TI 计算结果做出触发决策，管理批处理队列。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from src.core.logger import get_logger

from .models import TIResult, TILevel, TriggerDecision, DecisionType

if TYPE_CHECKING:
    from src.ingest.manictime.models import ActivityEvent

logger = get_logger(__name__)


@dataclass
class TriggerThresholds:
    """
    触发阈值配置

    Attributes:
        immediate_threshold: 立即触发阈值 (默认 0.7)
        batch_threshold: 批处理阈值 (默认 0.4)
        skip_threshold: 跳过阈值 (默认 0.2)
    """
    immediate_threshold: float = 0.7
    batch_threshold: float = 0.4
    skip_threshold: float = 0.2

    def __post_init__(self) -> None:
        """验证阈值配置"""
        if not (self.skip_threshold < self.batch_threshold < self.immediate_threshold):
            raise ValueError(
                "阈值必须满足: skip < batch < immediate"
            )


@dataclass
class BatchQueueItem:
    """
    批处理队列项

    Attributes:
        activity: 活动事件
        ti_result: TI 计算结果
        added_at: 加入队列时间
    """
    activity: ActivityEvent
    ti_result: TIResult
    added_at: datetime = field(default_factory=datetime.now)


class TriggerManager:
    """
    触发管理器

    根据 TI 分数决定是否触发 VLM 分析，并管理批处理队列

    Attributes:
        thresholds: 触发阈值配置
        batch_queue: 批处理队列
        max_batch_size: 最大批处理大小
        batch_timeout_seconds: 批处理超时时间(秒)
    """

    def __init__(
        self,
        thresholds: Optional[TriggerThresholds] = None,
        max_batch_size: int = 10,
        batch_timeout_seconds: int = 300,
    ) -> None:
        """
        初始化触发管理器

        Args:
            thresholds: 触发阈值配置
            max_batch_size: 最大批处理大小
            batch_timeout_seconds: 批处理超时时间(秒)
        """
        self._thresholds = thresholds or TriggerThresholds()
        self._max_batch_size = max_batch_size
        self._batch_timeout = timedelta(seconds=batch_timeout_seconds)
        self._batch_queue: deque[BatchQueueItem] = deque()
        self._delayed_items: dict[UUID, BatchQueueItem] = {}
        self._stats = {
            "total_decisions": 0,
            "immediate_count": 0,
            "batch_count": 0,
            "skip_count": 0,
            "delay_count": 0,
        }

    @property
    def thresholds(self) -> TriggerThresholds:
        """获取阈值配置"""
        return self._thresholds

    @property
    def batch_queue_size(self) -> int:
        """获取批处理队列大小"""
        return len(self._batch_queue)

    @property
    def stats(self) -> dict:
        """获取统计信息"""
        return {
            **self._stats,
            "batch_queue_size": self.batch_queue_size,
            "delayed_count": len(self._delayed_items),
        }

    def evaluate(
        self,
        activity: ActivityEvent,
        ti_result: TIResult,
    ) -> TriggerDecision:
        """
        评估触发决策

        Args:
            activity: 活动事件
            ti_result: TI 计算结果

        Returns:
            TriggerDecision: 触发决策
        """
        self._stats["total_decisions"] += 1

        # 检查是否需要延迟
        if ti_result.should_delay:
            decision = self._handle_delay(activity, ti_result)
            self._stats["delay_count"] += 1
            return decision

        # 根据 TI 分数决策
        score = ti_result.ti_score

        if score >= self._thresholds.immediate_threshold:
            decision = self._handle_immediate(activity, ti_result)
            self._stats["immediate_count"] += 1
        elif score >= self._thresholds.batch_threshold:
            decision = self._handle_batch(activity, ti_result)
            self._stats["batch_count"] += 1
        else:
            decision = self._handle_skip(activity, ti_result)
            self._stats["skip_count"] += 1

        logger.debug(
            f"触发决策: event={activity.event_id}, "
            f"ti={score:.3f}, decision={decision.decision_type.value}"
        )

        return decision

    def _handle_immediate(
        self,
        activity: ActivityEvent,
        ti_result: TIResult,
    ) -> TriggerDecision:
        """处理立即触发"""
        # 计算优先级: TI 越高优先级越高
        priority = min(10, int(ti_result.ti_score * 10) + 2)

        return TriggerDecision.create_immediate(
            event_id=activity.event_id,
            ti_score=ti_result.ti_score,
            reason=f"TI 分数 {ti_result.ti_score:.3f} 超过立即触发阈值",
            priority=priority,
        )

    def _handle_batch(
        self,
        activity: ActivityEvent,
        ti_result: TIResult,
    ) -> TriggerDecision:
        """处理批处理"""
        # 添加到批处理队列
        self._batch_queue.append(BatchQueueItem(
            activity=activity,
            ti_result=ti_result,
        ))

        # 确定批处理分组
        batch_group = self._get_batch_group(activity)

        return TriggerDecision.create_batch(
            event_id=activity.event_id,
            ti_score=ti_result.ti_score,
            batch_group=batch_group,
            reason=f"TI 分数 {ti_result.ti_score:.3f} 在批处理范围",
        )

    def _handle_skip(
        self,
        activity: ActivityEvent,
        ti_result: TIResult,
    ) -> TriggerDecision:
        """处理跳过"""
        return TriggerDecision.create_skip(
            event_id=activity.event_id,
            ti_score=ti_result.ti_score,
            reason=f"TI 分数 {ti_result.ti_score:.3f} 低于批处理阈值",
        )

    def _handle_delay(
        self,
        activity: ActivityEvent,
        ti_result: TIResult,
    ) -> TriggerDecision:
        """处理延迟"""
        delay_until = datetime.now() + timedelta(seconds=ti_result.delay_seconds)

        # 存储延迟项
        self._delayed_items[activity.event_id] = BatchQueueItem(
            activity=activity,
            ti_result=ti_result,
        )

        return TriggerDecision.create_delay(
            event_id=activity.event_id,
            ti_score=ti_result.ti_score,
            delay_until=delay_until,
            reason=f"延迟 {ti_result.delay_seconds} 秒处理",
        )

    def _get_batch_group(self, activity: ActivityEvent) -> str:
        """确定批处理分组"""
        # 按应用程序分组
        return f"app:{activity.application}"

    def check_batch_ready(self) -> list[tuple[ActivityEvent, TIResult]]:
        """
        检查批处理队列是否就绪

        Returns:
            就绪的活动和 TI 结果列表
        """
        ready_items: list[tuple[ActivityEvent, TIResult]] = []
        now = datetime.now()

        # 检查队列大小或超时
        while self._batch_queue:
            item = self._batch_queue[0]

            # 检查超时
            if now - item.added_at >= self._batch_timeout:
                self._batch_queue.popleft()
                ready_items.append((item.activity, item.ti_result))
                continue

            # 检查队列大小
            if len(self._batch_queue) >= self._max_batch_size:
                self._batch_queue.popleft()
                ready_items.append((item.activity, item.ti_result))
                continue

            # 未达到条件，停止检查
            break

        return ready_items

    def check_delayed_ready(self) -> list[tuple[ActivityEvent, TIResult]]:
        """
        检查延迟项是否就绪

        Returns:
            就绪的活动和 TI 结果列表
        """
        ready_items: list[tuple[ActivityEvent, TIResult]] = []
        now = datetime.now()

        expired_ids = []
        for event_id, item in self._delayed_items.items():
            delay_seconds = item.ti_result.delay_seconds
            if now - item.added_at >= timedelta(seconds=delay_seconds):
                ready_items.append((item.activity, item.ti_result))
                expired_ids.append(event_id)

        # 移除已处理的延迟项
        for event_id in expired_ids:
            del self._delayed_items[event_id]

        return ready_items

    def flush_batch_queue(self) -> list[tuple[ActivityEvent, TIResult]]:
        """
        强制刷新批处理队列

        Returns:
            所有队列中的活动和 TI 结果
        """
        items = [(item.activity, item.ti_result) for item in self._batch_queue]
        self._batch_queue.clear()
        return items

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "total_decisions": 0,
            "immediate_count": 0,
            "batch_count": 0,
            "skip_count": 0,
            "delay_count": 0,
        }
