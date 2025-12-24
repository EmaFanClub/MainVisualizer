"""
Senatus 智能触发模块

负责分析活动序列，计算 Taboo Index (ti)，决定是否触发 VLM 深度分析。
采用三级级联推理架构以最小化 VLM 调用成本。

公开接口:
    - SenatusEngine: 主引擎类
    - TIResult: TI 计算结果数据类
    - TriggerDecision: 触发决策数据类
    - TILevel: TI 级别枚举
    - DecisionType: 决策类型枚举

使用示例:
    >>> from src.senatus import SenatusEngine, DecisionType
    >>> from src.ingest.manictime import ManicTimeDBConnector, ActivityParser
    >>>
    >>> # 初始化引擎
    >>> engine = SenatusEngine()
    >>>
    >>> # 处理活动
    >>> with ManicTimeDBConnector(db_path) as db:
    ...     activities = db.query_activities(start, end)
    ...     parser = ActivityParser()
    ...     for raw in activities:
    ...         event = parser.parse_from_dict(raw, app_info)
    ...         decision = engine.process_activity(event)
    ...         if decision.decision_type == DecisionType.IMMEDIATE:
    ...             # 立即触发 VLM 分析
    ...             pass
"""

from .engine import SenatusEngine
from .models import (
    TIResult,
    TILevel,
    ComponentScore,
    TriggerDecision,
    DecisionType,
)
from .ti_calculator import TabooIndexCalculator
from .trigger_manager import TriggerManager, TriggerThresholds
from .filters import (
    BaseFilter,
    FilterResult,
    WhitelistFilter,
    BlacklistFilter,
    TimeRuleFilter,
    TimeRule,
    StaticFrameFilter,
)
from .analyzers import (
    BaseAnalyzer,
    AnalyzerResult,
    MetadataAnalyzer,
    VisualAnalyzer,
    FrameDiffAnalyzer,
    ContextSwitchAnalyzer,
    UncertaintyAnalyzer,
)

__all__ = [
    # 主引擎
    "SenatusEngine",
    # 数据模型
    "TIResult",
    "TILevel",
    "ComponentScore",
    "TriggerDecision",
    "DecisionType",
    # 核心组件
    "TabooIndexCalculator",
    "TriggerManager",
    "TriggerThresholds",
    # 过滤器
    "BaseFilter",
    "FilterResult",
    "WhitelistFilter",
    "BlacklistFilter",
    "TimeRuleFilter",
    "TimeRule",
    "StaticFrameFilter",
    # 分析器
    "BaseAnalyzer",
    "AnalyzerResult",
    "MetadataAnalyzer",
    "VisualAnalyzer",
    "FrameDiffAnalyzer",
    "ContextSwitchAnalyzer",
    "UncertaintyAnalyzer",
]
