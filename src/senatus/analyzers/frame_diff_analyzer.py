"""
帧差异分析器

计算当前帧与历史帧的差异程度，快速变化的屏幕可能表示重要活动。
权重: 0.15
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from .base_analyzer import BaseAnalyzer, AnalyzerResult

if TYPE_CHECKING:
    from PIL import Image
    from src.ingest.manictime.models import ActivityEvent


@dataclass
class FrameRecord:
    """
    帧记录

    Attributes:
        event_id: 活动事件 ID
        timestamp: 时间戳
        histogram: 灰度直方图
    """
    event_id: str
    timestamp: datetime
    histogram: list[int]


def _compute_histogram(image: Image.Image) -> list[int]:
    """
    计算图像的灰度直方图

    Args:
        image: PIL 图像对象

    Returns:
        256 个 bin 的直方图
    """
    # 转换为灰度图
    if image.mode != 'L':
        gray = image.convert('L')
    else:
        gray = image

    return gray.histogram()


def _histogram_difference(hist1: list[int], hist2: list[int]) -> float:
    """
    计算两个直方图之间的差异

    使用卡方距离

    Args:
        hist1: 第一个直方图
        hist2: 第二个直方图

    Returns:
        归一化的差异值 (0.0-1.0)
    """
    if len(hist1) != len(hist2):
        return 1.0

    chi_squared = 0.0
    total1 = sum(hist1)
    total2 = sum(hist2)

    if total1 == 0 or total2 == 0:
        return 1.0

    # 归一化直方图
    norm1 = [h / total1 for h in hist1]
    norm2 = [h / total2 for h in hist2]

    for n1, n2 in zip(norm1, norm2):
        if n1 + n2 > 0:
            chi_squared += (n1 - n2) ** 2 / (n1 + n2)

    # 归一化到 0-1
    # 卡方距离最大值约为 2.0
    normalized = min(1.0, chi_squared / 2.0)

    return normalized


# 差异等级映射
DIFF_LEVEL_MAP = [
    (0.05, "static", 0.05),       # diff < 0.05: 静止
    (0.2, "slow_change", 0.3),    # 0.05 <= diff < 0.2: 缓慢变化
    (0.5, "fast_change", 0.6),    # 0.2 <= diff < 0.5: 快速变化
    (1.0, "dramatic", 0.8),       # diff >= 0.5: 剧烈变化
]


class FrameDiffAnalyzer(BaseAnalyzer):
    """
    帧差异分析器

    计算当前帧与历史帧的差异程度

    差异等级映射:
    - diff < 0.05: 静止 -> score = 0.05
    - 0.05 <= diff < 0.2: 缓慢变化 -> score = 0.3
    - 0.2 <= diff < 0.5: 快速变化 -> score = 0.6
    - diff >= 0.5: 剧烈变化 -> score = 0.8

    Attributes:
        history_size: 历史帧数量
    """

    def __init__(
        self,
        weight: float = 0.15,
        history_size: int = 3,
        enabled: bool = True,
    ) -> None:
        """
        初始化帧差异分析器

        Args:
            weight: 权重
            history_size: 保留的历史帧数量
            enabled: 是否启用
        """
        super().__init__(name="frame_diff", weight=weight, enabled=enabled)

        self._history_size = max(1, history_size)
        self._history: deque[FrameRecord] = deque(maxlen=history_size)

        # 扩展统计
        self._stats.update({
            "static_count": 0,
            "slow_change_count": 0,
            "fast_change_count": 0,
            "dramatic_change_count": 0,
        })

    def _do_analyze(
        self,
        activity: ActivityEvent,
        screenshot: Optional[Image.Image] = None,
    ) -> AnalyzerResult:
        """
        执行帧差异分析

        Args:
            activity: 活动事件
            screenshot: 关联截图(可选)

        Returns:
            AnalyzerResult: 分析结果
        """
        # 如果没有截图，返回低置信度结果
        if screenshot is None:
            return AnalyzerResult(
                analyzer_name=self.name,
                score=0.3,  # 默认中等分数
                confidence=0.3,
                reason="无截图，无法分析帧差异",
                details={"has_screenshot": False},
            )

        # 计算当前帧的直方图
        current_histogram = _compute_histogram(screenshot)

        # 与历史帧比较
        if not self._history:
            # 第一帧，无历史可比较
            self._add_to_history(activity, current_histogram)
            return AnalyzerResult(
                analyzer_name=self.name,
                score=0.3,  # 默认中等分数
                confidence=0.5,
                reason="首帧，无历史比较",
                details={
                    "has_screenshot": True,
                    "is_first_frame": True,
                },
            )

        # 计算与最近帧的差异
        recent_diffs = []
        for record in self._history:
            diff = _histogram_difference(current_histogram, record.histogram)
            recent_diffs.append(diff)

        # 使用平均差异
        avg_diff = sum(recent_diffs) / len(recent_diffs)

        # 添加到历史
        self._add_to_history(activity, current_histogram)

        # 映射到分数
        score, level = self._map_diff_to_score(avg_diff)

        # 更新统计
        self._update_level_stats(level)

        return AnalyzerResult(
            analyzer_name=self.name,
            score=score,
            confidence=0.8,
            reason=f"帧差异: {level} (avg_diff={avg_diff:.3f})",
            details={
                "has_screenshot": True,
                "avg_diff": avg_diff,
                "diff_level": level,
                "history_size": len(self._history),
                "individual_diffs": recent_diffs,
            },
        )

    def _add_to_history(
        self,
        activity: ActivityEvent,
        histogram: list[int],
    ) -> None:
        """添加帧到历史"""
        record = FrameRecord(
            event_id=str(activity.event_id),
            timestamp=activity.timestamp,
            histogram=histogram,
        )
        self._history.append(record)

    def _map_diff_to_score(self, diff: float) -> tuple[float, str]:
        """
        将差异值映射到分数

        Args:
            diff: 差异值

        Returns:
            (分数, 级别名称) 元组
        """
        for threshold, level, score in DIFF_LEVEL_MAP:
            if diff < threshold:
                return score, level

        # 默认返回最高级别
        return DIFF_LEVEL_MAP[-1][2], DIFF_LEVEL_MAP[-1][1]

    def _update_level_stats(self, level: str) -> None:
        """更新级别统计"""
        stat_key = f"{level}_count"
        if stat_key in self._stats:
            self._stats[stat_key] += 1

    def clear_history(self) -> None:
        """清除历史记录"""
        self._history.clear()

    def get_recent_diffs(self) -> list[float]:
        """
        获取最近的帧差异值

        计算相邻历史帧之间的差异

        Returns:
            差异值列表
        """
        if len(self._history) < 2:
            return []

        diffs = []
        history_list = list(self._history)

        for i in range(1, len(history_list)):
            diff = _histogram_difference(
                history_list[i].histogram,
                history_list[i - 1].histogram,
            )
            diffs.append(diff)

        return diffs

    def compare_frames(
        self,
        frame1: Image.Image,
        frame2: Image.Image,
    ) -> float:
        """
        比较两帧之间的差异

        Args:
            frame1: 第一帧
            frame2: 第二帧

        Returns:
            差异值 (0.0-1.0)
        """
        hist1 = _compute_histogram(frame1)
        hist2 = _compute_histogram(frame2)
        return _histogram_difference(hist1, hist2)

    @property
    def history_size(self) -> int:
        """获取历史大小"""
        return self._history_size

    @property
    def current_history_length(self) -> int:
        """获取当前历史长度"""
        return len(self._history)

    @property
    def level_distribution(self) -> dict:
        """获取级别分布统计"""
        total = sum([
            self._stats["static_count"],
            self._stats["slow_change_count"],
            self._stats["fast_change_count"],
            self._stats["dramatic_change_count"],
        ])

        if total == 0:
            return {}

        return {
            "static": self._stats["static_count"] / total,
            "slow_change": self._stats["slow_change_count"] / total,
            "fast_change": self._stats["fast_change_count"] / total,
            "dramatic": self._stats["dramatic_change_count"] / total,
        }
