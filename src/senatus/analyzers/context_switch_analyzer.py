"""
上下文切换分析器

检测窗口切换模式和认知成本。频繁的上下文切换可能表示对比工作或焦虑状态。
权重: 0.15
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from .base_analyzer import BaseAnalyzer, AnalyzerResult

if TYPE_CHECKING:
    from PIL import Image
    from src.ingest.manictime.models import ActivityEvent


@dataclass
class SwitchRecord:
    """
    切换记录

    Attributes:
        event_id: 活动事件 ID
        timestamp: 时间戳
        application: 应用名称
        window_title: 窗口标题
    """
    event_id: str
    timestamp: datetime
    application: str
    window_title: str


@dataclass
class SwitchPattern:
    """
    切换模式

    Attributes:
        pattern_type: 模式类型
        frequency: 切换频率
        involved_apps: 涉及的应用
        score: 模式评分
    """
    pattern_type: str
    frequency: float
    involved_apps: list[str]
    score: float


# 应用切换成本矩阵
# 从深度工作应用切换到浅工作应用的成本更高
APP_DEPTH_LEVELS = {
    "deep_work": [
        "code", "vscode", "visual studio",
        "pycharm", "idea", "webstorm",
        "word", "excel", "powerpoint",
        "acrobat", "pdf",
    ],
    "medium_work": [
        "outlook", "teams", "slack",
        "chrome", "firefox", "edge",
        "terminal", "powershell",
    ],
    "shallow_work": [
        "telegram", "discord", "wechat", "qq",
        "twitter", "facebook", "youtube",
        "spotify", "steam",
    ],
}


def _get_app_depth(app_name: str) -> int:
    """
    获取应用的工作深度级别

    Args:
        app_name: 应用名称

    Returns:
        深度级别 (0=浅, 1=中, 2=深)
    """
    app_lower = app_name.lower()

    for keyword in APP_DEPTH_LEVELS["deep_work"]:
        if keyword in app_lower:
            return 2

    for keyword in APP_DEPTH_LEVELS["medium_work"]:
        if keyword in app_lower:
            return 1

    for keyword in APP_DEPTH_LEVELS["shallow_work"]:
        if keyword in app_lower:
            return 0

    return 1  # 默认中等深度


def _compute_switch_cost(from_app: str, to_app: str) -> float:
    """
    计算切换成本

    从深度工作到浅工作的切换成本最高

    Args:
        from_app: 源应用
        to_app: 目标应用

    Returns:
        切换成本 (0.0-1.0)
    """
    from_depth = _get_app_depth(from_app)
    to_depth = _get_app_depth(to_app)

    # 深度下降 = 高成本
    if from_depth > to_depth:
        return 0.8 + (from_depth - to_depth) * 0.1

    # 深度上升 = 中等成本
    if from_depth < to_depth:
        return 0.4 + (to_depth - from_depth) * 0.1

    # 同级别切换 = 低成本
    return 0.2


class ContextSwitchAnalyzer(BaseAnalyzer):
    """
    上下文切换分析器

    检测窗口切换模式:
    1. 快速切换检测 - 3秒内多次切换
    2. A-B-A-B 模式 - 对比工作模式
    3. 切换成本评估 - 深度工作 -> 浅工作

    Attributes:
        context_window_size: 上下文窗口大小
        rapid_switch_threshold: 快速切换阈值(秒)
    """

    def __init__(
        self,
        weight: float = 0.15,
        context_window_size: int = 10,
        rapid_switch_threshold: float = 3.0,
        enabled: bool = True,
    ) -> None:
        """
        初始化上下文切换分析器

        Args:
            weight: 权重
            context_window_size: 上下文窗口大小
            rapid_switch_threshold: 快速切换阈值(秒)
            enabled: 是否启用
        """
        super().__init__(name="context_switch", weight=weight, enabled=enabled)

        self._context_window_size = max(3, context_window_size)
        self._rapid_switch_threshold = rapid_switch_threshold
        self._history: deque[SwitchRecord] = deque(maxlen=context_window_size)

        # 扩展统计
        self._stats.update({
            "rapid_switches": 0,
            "abab_patterns": 0,
            "high_cost_switches": 0,
        })

    def _do_analyze(
        self,
        activity: ActivityEvent,
        screenshot: Optional[Image.Image] = None,
    ) -> AnalyzerResult:
        """
        执行上下文切换分析

        Args:
            activity: 活动事件
            screenshot: 关联截图(未使用)

        Returns:
            AnalyzerResult: 分析结果
        """
        # 添加当前活动到历史
        current_record = SwitchRecord(
            event_id=str(activity.event_id),
            timestamp=activity.timestamp,
            application=activity.application,
            window_title=activity.window_title,
        )

        # 如果历史不足，只添加记录
        if len(self._history) < 2:
            self._history.append(current_record)
            return AnalyzerResult(
                analyzer_name=self.name,
                score=0.2,  # 默认低分
                confidence=0.5,
                reason="历史记录不足，无法分析切换模式",
                details={
                    "history_size": len(self._history),
                },
            )

        # 分析切换模式
        patterns = self._analyze_patterns(current_record)

        # 添加到历史
        self._history.append(current_record)

        # 计算综合分数
        score, reason = self._compute_final_score(patterns)

        return AnalyzerResult(
            analyzer_name=self.name,
            score=score,
            confidence=0.75,
            reason=reason,
            details={
                "patterns": [
                    {
                        "type": p.pattern_type,
                        "frequency": p.frequency,
                        "apps": p.involved_apps,
                        "score": p.score,
                    }
                    for p in patterns
                ],
                "history_size": len(self._history),
            },
        )

    def _analyze_patterns(
        self,
        current: SwitchRecord,
    ) -> list[SwitchPattern]:
        """
        分析切换模式

        Args:
            current: 当前活动记录

        Returns:
            检测到的模式列表
        """
        patterns = []

        # 1. 检测快速切换
        rapid_pattern = self._detect_rapid_switching(current)
        if rapid_pattern:
            patterns.append(rapid_pattern)
            self._stats["rapid_switches"] += 1

        # 2. 检测 A-B-A-B 模式
        abab_pattern = self._detect_abab_pattern(current)
        if abab_pattern:
            patterns.append(abab_pattern)
            self._stats["abab_patterns"] += 1

        # 3. 计算切换成本
        cost_pattern = self._compute_switch_cost_pattern(current)
        if cost_pattern:
            patterns.append(cost_pattern)
            if cost_pattern.score > 0.6:
                self._stats["high_cost_switches"] += 1

        return patterns

    def _detect_rapid_switching(
        self,
        current: SwitchRecord,
    ) -> Optional[SwitchPattern]:
        """
        检测快速切换

        在 rapid_switch_threshold 秒内发生的切换

        Args:
            current: 当前记录

        Returns:
            快速切换模式或 None
        """
        if not self._history:
            return None

        last_record = self._history[-1]

        # 检查时间间隔
        time_diff = (current.timestamp - last_record.timestamp).total_seconds()

        if time_diff < self._rapid_switch_threshold:
            # 检查是否真的是不同的应用
            if current.application.lower() != last_record.application.lower():
                # 计算最近的快速切换频率
                rapid_count = self._count_rapid_switches_in_window()

                return SwitchPattern(
                    pattern_type="rapid_switch",
                    frequency=rapid_count / max(1, len(self._history)),
                    involved_apps=[last_record.application, current.application],
                    score=min(0.9, 0.4 + rapid_count * 0.15),
                )

        return None

    def _count_rapid_switches_in_window(self) -> int:
        """计算窗口内的快速切换次数"""
        if len(self._history) < 2:
            return 0

        count = 0
        history_list = list(self._history)

        for i in range(1, len(history_list)):
            time_diff = (
                history_list[i].timestamp - history_list[i - 1].timestamp
            ).total_seconds()

            if time_diff < self._rapid_switch_threshold:
                if (history_list[i].application.lower() !=
                        history_list[i - 1].application.lower()):
                    count += 1

        return count

    def _detect_abab_pattern(
        self,
        current: SwitchRecord,
    ) -> Optional[SwitchPattern]:
        """
        检测 A-B-A-B 对比模式

        两个应用之间的交替切换

        Args:
            current: 当前记录

        Returns:
            ABAB模式或 None
        """
        if len(self._history) < 3:
            return None

        history_list = list(self._history)

        # 获取最近4个应用(包括当前)
        apps = [r.application.lower() for r in history_list[-3:]]
        apps.append(current.application.lower())

        # 检查 A-B-A-B 模式
        if len(apps) >= 4:
            if apps[0] == apps[2] and apps[1] == apps[3] and apps[0] != apps[1]:
                return SwitchPattern(
                    pattern_type="abab_comparison",
                    frequency=1.0,
                    involved_apps=[
                        history_list[-3].application,
                        history_list[-2].application,
                    ],
                    score=0.7,
                )

        return None

    def _compute_switch_cost_pattern(
        self,
        current: SwitchRecord,
    ) -> Optional[SwitchPattern]:
        """
        计算切换成本模式

        Args:
            current: 当前记录

        Returns:
            切换成本模式或 None
        """
        if not self._history:
            return None

        last_record = self._history[-1]

        # 如果是同一个应用，无切换成本
        if current.application.lower() == last_record.application.lower():
            return None

        cost = _compute_switch_cost(last_record.application, current.application)

        return SwitchPattern(
            pattern_type="switch_cost",
            frequency=0.0,
            involved_apps=[last_record.application, current.application],
            score=cost,
        )

    def _compute_final_score(
        self,
        patterns: list[SwitchPattern],
    ) -> tuple[float, str]:
        """
        计算最终分数

        Args:
            patterns: 检测到的模式列表

        Returns:
            (分数, 原因) 元组
        """
        if not patterns:
            return 0.1, "无明显切换模式"

        # 取最高分的模式
        max_pattern = max(patterns, key=lambda p: p.score)

        # 多模式叠加加分
        bonus = min(0.15, (len(patterns) - 1) * 0.05)
        final_score = min(1.0, max_pattern.score + bonus)

        # 构建原因
        reason_parts = []
        for p in patterns:
            if p.pattern_type == "rapid_switch":
                reason_parts.append(f"快速切换(频率:{p.frequency:.2f})")
            elif p.pattern_type == "abab_comparison":
                reason_parts.append("对比模式")
            elif p.pattern_type == "switch_cost":
                reason_parts.append(f"切换成本:{p.score:.2f}")

        return final_score, "; ".join(reason_parts)

    def clear_history(self) -> None:
        """清除历史记录"""
        self._history.clear()

    def set_context_window(self, activities: list[ActivityEvent]) -> None:
        """
        设置上下文窗口

        用于从外部注入历史活动

        Args:
            activities: 历史活动列表
        """
        self._history.clear()
        for activity in activities[-self._context_window_size:]:
            record = SwitchRecord(
                event_id=str(activity.event_id),
                timestamp=activity.timestamp,
                application=activity.application,
                window_title=activity.window_title,
            )
            self._history.append(record)

    @property
    def context_window_size(self) -> int:
        """获取上下文窗口大小"""
        return self._context_window_size

    @property
    def current_history_length(self) -> int:
        """获取当前历史长度"""
        return len(self._history)

    @property
    def switch_pattern_stats(self) -> dict:
        """获取切换模式统计"""
        return {
            "rapid_switches": self._stats["rapid_switches"],
            "abab_patterns": self._stats["abab_patterns"],
            "high_cost_switches": self._stats["high_cost_switches"],
        }
