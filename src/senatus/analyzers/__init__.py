"""
Senatus 分析器

Stage 2 轻量分析器，用于计算活动的各个评分组件。
"""

from .base_analyzer import BaseAnalyzer, AnalyzerResult
from .metadata_analyzer import MetadataAnalyzer
from .visual_analyzer import VisualAnalyzer
from .frame_diff_analyzer import FrameDiffAnalyzer
from .context_switch_analyzer import ContextSwitchAnalyzer
from .uncertainty_analyzer import UncertaintyAnalyzer

__all__ = [
    "BaseAnalyzer",
    "AnalyzerResult",
    "MetadataAnalyzer",
    "VisualAnalyzer",
    "FrameDiffAnalyzer",
    "ContextSwitchAnalyzer",
    "UncertaintyAnalyzer",
]
