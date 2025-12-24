"""
Senatus 数据模型

定义 Senatus 模块使用的所有数据模型。
"""

from .ti_result import TIResult, TILevel, ComponentScore
from .trigger_decision import TriggerDecision, DecisionType

__all__ = [
    "TIResult",
    "TILevel",
    "ComponentScore",
    "TriggerDecision",
    "DecisionType",
]
