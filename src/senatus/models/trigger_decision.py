"""
触发决策模型

定义 Senatus 模块的最终输出 - 是否触发 VLM 分析的决策。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class DecisionType(str, Enum):
    """
    触发决策类型枚举
    """
    IMMEDIATE = "immediate"     # 立即触发 VLM 分析
    BATCH = "batch"             # 加入批处理队列
    SKIP = "skip"               # 跳过，不需要 VLM 分析
    DELAY = "delay"             # 延迟处理(如新建文档等场景)
    FILTERED = "filtered"       # 被过滤器过滤


@dataclass
class TriggerDecision:
    """
    触发决策结果

    Senatus 模块的最终输出，决定活动事件是否需要 VLM 深度分析

    Attributes:
        event_id: 关联的活动事件 ID
        decision_type: 决策类型
        ti_score: TI 分数(如有)
        reason: 决策原因说明
        filter_name: 触发过滤器名称(如被过滤)
        priority: 处理优先级 (1-10, 10 最高)
        delay_until: 延迟处理的目标时间
        batch_group: 批处理分组标识
        created_at: 决策创建时间
        metadata: 额外元数据
    """
    event_id: UUID
    decision_type: DecisionType
    ti_score: Optional[float] = None
    reason: str = ""
    filter_name: Optional[str] = None
    priority: int = 5
    delay_until: Optional[datetime] = None
    batch_group: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """验证数据一致性"""
        # 验证优先级范围
        self.priority = max(1, min(10, self.priority))

        # 验证决策类型与字段的一致性
        if self.decision_type == DecisionType.FILTERED and not self.filter_name:
            self.filter_name = "unknown"

        if self.decision_type == DecisionType.DELAY and not self.delay_until:
            # 默认延迟 5 分钟
            from datetime import timedelta
            self.delay_until = datetime.now() + timedelta(minutes=5)

    @classmethod
    def create_immediate(
        cls,
        event_id: UUID,
        ti_score: float,
        reason: str = "TI 分数超过阈值",
        priority: int = 8,
    ) -> TriggerDecision:
        """创建立即触发决策"""
        return cls(
            event_id=event_id,
            decision_type=DecisionType.IMMEDIATE,
            ti_score=ti_score,
            reason=reason,
            priority=priority,
        )

    @classmethod
    def create_batch(
        cls,
        event_id: UUID,
        ti_score: float,
        batch_group: Optional[str] = None,
        reason: str = "TI 分数在批处理范围",
    ) -> TriggerDecision:
        """创建批处理决策"""
        return cls(
            event_id=event_id,
            decision_type=DecisionType.BATCH,
            ti_score=ti_score,
            reason=reason,
            batch_group=batch_group or "default",
            priority=5,
        )

    @classmethod
    def create_skip(
        cls,
        event_id: UUID,
        ti_score: Optional[float] = None,
        reason: str = "TI 分数过低",
    ) -> TriggerDecision:
        """创建跳过决策"""
        return cls(
            event_id=event_id,
            decision_type=DecisionType.SKIP,
            ti_score=ti_score,
            reason=reason,
            priority=1,
        )

    @classmethod
    def create_filtered(
        cls,
        event_id: UUID,
        filter_name: str,
        reason: str = "",
    ) -> TriggerDecision:
        """创建过滤决策"""
        return cls(
            event_id=event_id,
            decision_type=DecisionType.FILTERED,
            reason=reason or f"被过滤器 {filter_name} 过滤",
            filter_name=filter_name,
            priority=1,
        )

    @classmethod
    def create_delay(
        cls,
        event_id: UUID,
        ti_score: float,
        delay_until: datetime,
        reason: str = "延迟处理",
    ) -> TriggerDecision:
        """创建延迟决策"""
        return cls(
            event_id=event_id,
            decision_type=DecisionType.DELAY,
            ti_score=ti_score,
            reason=reason,
            delay_until=delay_until,
            priority=3,
        )

    @property
    def should_analyze(self) -> bool:
        """是否需要进行 VLM 分析"""
        return self.decision_type in (DecisionType.IMMEDIATE, DecisionType.BATCH)

    @property
    def is_immediate(self) -> bool:
        """是否需要立即分析"""
        return self.decision_type == DecisionType.IMMEDIATE

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "event_id": str(self.event_id),
            "decision_type": self.decision_type.value,
            "ti_score": self.ti_score,
            "reason": self.reason,
            "filter_name": self.filter_name,
            "priority": self.priority,
            "delay_until": self.delay_until.isoformat() if self.delay_until else None,
            "batch_group": self.batch_group,
            "created_at": self.created_at.isoformat(),
            "should_analyze": self.should_analyze,
        }
