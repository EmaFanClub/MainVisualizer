"""
Taboo Index (TI) 计算结果模型

定义 TI 计算的结果数据结构，包括分数、级别和各组件得分。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID


class TILevel(str, Enum):
    """
    TI 级别枚举

    根据 ti_score 划分的敏感度级别
    """
    HIGH = "high"           # ti > 0.7, 高敏感度
    MEDIUM = "medium"       # 0.4 < ti <= 0.7, 中等敏感度
    LOW = "low"             # 0.2 < ti <= 0.4, 低敏感度
    MINIMAL = "minimal"     # ti <= 0.2, 极低敏感度


@dataclass
class ComponentScore:
    """
    单个评分组件的结果

    记录某个评分维度的分数和权重
    """
    name: str                           # 组件名称
    score: float                        # 原始分数 (0.0 - 1.0)
    weight: float                       # 权重
    weighted_score: float               # 加权分数 = score * weight
    reason: str = ""                    # 评分原因说明

    def __post_init__(self) -> None:
        """验证分数范围"""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"分数必须在 0.0-1.0 范围内: {self.score}")
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"权重必须在 0.0-1.0 范围内: {self.weight}")


@dataclass
class TIResult:
    """
    Taboo Index 计算结果

    包含完整的 TI 计算结果，供触发决策使用

    Attributes:
        event_id: 关联的活动事件 ID
        ti_score: 最终 TI 分数 (0.0 - 1.0)
        ti_level: TI 级别 (HIGH/MEDIUM/LOW/MINIMAL)
        component_scores: 各组件的评分详情
        confidence: 计算置信度 (0.0 - 1.0)
        should_delay: 是否应延迟处理
        delay_seconds: 建议延迟时间(秒)
        raw_analysis: 原始分析数据(用于调试)
    """
    event_id: UUID
    ti_score: float
    ti_level: TILevel
    component_scores: dict[str, ComponentScore] = field(default_factory=dict)
    confidence: float = 1.0
    should_delay: bool = False
    delay_seconds: int = 0
    raw_analysis: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """验证并规范化数据"""
        # 确保分数在有效范围内
        self.ti_score = max(0.0, min(1.0, self.ti_score))
        self.confidence = max(0.0, min(1.0, self.confidence))

        # 如果未设置级别，根据分数自动计算
        if self.ti_level is None:
            self.ti_level = self._calculate_level(self.ti_score)

    @staticmethod
    def _calculate_level(score: float) -> TILevel:
        """根据分数计算级别"""
        if score > 0.7:
            return TILevel.HIGH
        elif score > 0.4:
            return TILevel.MEDIUM
        elif score > 0.2:
            return TILevel.LOW
        else:
            return TILevel.MINIMAL

    @classmethod
    def create_minimal(cls, event_id: UUID) -> TIResult:
        """
        创建最小 TI 结果

        用于被过滤器跳过的活动
        """
        return cls(
            event_id=event_id,
            ti_score=0.0,
            ti_level=TILevel.MINIMAL,
            confidence=1.0,
        )

    @classmethod
    def create_from_scores(
        cls,
        event_id: UUID,
        component_scores: dict[str, ComponentScore],
        confidence: float = 1.0,
        should_delay: bool = False,
        delay_seconds: int = 0,
    ) -> TIResult:
        """
        从组件分数创建 TI 结果

        自动计算总分和级别
        """
        # 计算加权总分
        total_score = sum(c.weighted_score for c in component_scores.values())
        total_weight = sum(c.weight for c in component_scores.values())

        # 归一化分数
        if total_weight > 0:
            ti_score = total_score / total_weight
        else:
            ti_score = 0.0

        ti_score = max(0.0, min(1.0, ti_score))
        ti_level = cls._calculate_level(ti_score)

        return cls(
            event_id=event_id,
            ti_score=ti_score,
            ti_level=ti_level,
            component_scores=component_scores,
            confidence=confidence,
            should_delay=should_delay,
            delay_seconds=delay_seconds,
        )

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "event_id": str(self.event_id),
            "ti_score": self.ti_score,
            "ti_level": self.ti_level.value,
            "component_scores": {
                name: {
                    "score": c.score,
                    "weight": c.weight,
                    "weighted_score": c.weighted_score,
                    "reason": c.reason,
                }
                for name, c in self.component_scores.items()
            },
            "confidence": self.confidence,
            "should_delay": self.should_delay,
            "delay_seconds": self.delay_seconds,
        }
