"""
不确定性分析器

评估当前分析的不确定性程度。高不确定性表示需要更深入的分析。
权重: 0.10 (最低权重)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from .base_analyzer import BaseAnalyzer, AnalyzerResult

if TYPE_CHECKING:
    from PIL import Image
    from src.ingest.manictime.models import ActivityEvent


# 不确定性来源及其权重
UNCERTAINTY_SOURCES = {
    "no_screenshot": {
        "weight": 0.30,
        "description": "无截图",
    },
    "empty_title": {
        "weight": 0.20,
        "description": "窗口标题为空",
    },
    "unknown_app": {
        "weight": 0.25,
        "description": "未知应用",
    },
    "short_duration": {
        "weight": 0.15,
        "description": "活动持续时间过短",
    },
    "generic_title": {
        "weight": 0.10,
        "description": "通用窗口标题",
    },
}

# 已知应用列表
KNOWN_APPS = [
    # 浏览器
    "chrome", "firefox", "edge", "brave", "opera", "safari",
    # 开发工具
    "code", "vscode", "visual studio", "pycharm", "idea", "webstorm",
    "sublime", "atom", "vim", "neovim", "emacs",
    # 终端
    "terminal", "powershell", "cmd", "iterm", "warp",
    # Office
    "word", "excel", "powerpoint", "outlook", "onenote",
    # 通讯
    "teams", "slack", "discord", "telegram", "wechat", "qq", "zoom",
    # 系统
    "explorer", "finder", "settings", "taskmgr",
    # 媒体
    "spotify", "vlc", "youtube", "netflix",
    # 其他
    "obsidian", "notion", "trello", "figma", "photoshop",
]

# 通用窗口标题（信息量低）
GENERIC_TITLES = [
    "untitled",
    "new",
    "document",
    "sheet",
    "presentation",
    "无标题",
    "新建",
    "未命名",
    "loading",
    "加载中",
    "please wait",
    "请稍候",
]


@dataclass
class UncertaintySources:
    """
    不确定性来源记录

    Attributes:
        sources: 不确定性来源列表及其贡献值
        total_score: 总不确定性分数
    """
    sources: dict = field(default_factory=dict)
    total_score: float = 0.0


class UncertaintyAnalyzer(BaseAnalyzer):
    """
    不确定性分析器

    评估当前分析的不确定性程度

    不确定性来源:
    - 无截图: +0.30
    - 窗口标题为空: +0.20
    - 未知应用: +0.25
    - 活动持续时间 < 5s: +0.15
    - 通用窗口标题: +0.10

    高不确定性建议进行 VLM 深度分析以获取更多信息

    Attributes:
        min_duration_threshold: 最短活动持续时间阈值(秒)
        known_apps: 已知应用列表
    """

    def __init__(
        self,
        weight: float = 0.10,
        min_duration_threshold: int = 5,
        enabled: bool = True,
        custom_known_apps: Optional[list[str]] = None,
    ) -> None:
        """
        初始化不确定性分析器

        Args:
            weight: 权重
            min_duration_threshold: 最短活动持续时间阈值(秒)
            enabled: 是否启用
            custom_known_apps: 自定义已知应用列表
        """
        super().__init__(name="uncertainty", weight=weight, enabled=enabled)

        self._min_duration_threshold = min_duration_threshold

        # 合并已知应用列表
        self._known_apps = set(app.lower() for app in KNOWN_APPS)
        if custom_known_apps:
            self._known_apps.update(app.lower() for app in custom_known_apps)

        self._generic_titles = [t.lower() for t in GENERIC_TITLES]

        # 扩展统计
        self._stats.update({
            "high_uncertainty_count": 0,
            "low_uncertainty_count": 0,
        })

    def _do_analyze(
        self,
        activity: ActivityEvent,
        screenshot: Optional[Image.Image] = None,
    ) -> AnalyzerResult:
        """
        执行不确定性分析

        Args:
            activity: 活动事件
            screenshot: 关联截图(可选)

        Returns:
            AnalyzerResult: 分析结果
        """
        sources = self._compute_uncertainty_sources(activity, screenshot)

        # 更新统计
        if sources.total_score > 0.5:
            self._stats["high_uncertainty_count"] += 1
        else:
            self._stats["low_uncertainty_count"] += 1

        return AnalyzerResult(
            analyzer_name=self.name,
            score=sources.total_score,
            confidence=0.9,  # 规则计算置信度高
            reason=self._build_reason(sources),
            details={
                "sources": sources.sources,
                "total_uncertainty": sources.total_score,
            },
        )

    def _compute_uncertainty_sources(
        self,
        activity: ActivityEvent,
        screenshot: Optional[Image.Image],
    ) -> UncertaintySources:
        """
        计算不确定性来源

        Args:
            activity: 活动事件
            screenshot: 截图

        Returns:
            UncertaintySources: 不确定性来源记录
        """
        sources = UncertaintySources()
        total = 0.0

        # 1. 检查截图
        if screenshot is None:
            weight = UNCERTAINTY_SOURCES["no_screenshot"]["weight"]
            sources.sources["no_screenshot"] = weight
            total += weight

        # 2. 检查窗口标题
        title = activity.window_title.strip()
        if not title:
            weight = UNCERTAINTY_SOURCES["empty_title"]["weight"]
            sources.sources["empty_title"] = weight
            total += weight
        elif self._is_generic_title(title):
            weight = UNCERTAINTY_SOURCES["generic_title"]["weight"]
            sources.sources["generic_title"] = weight
            total += weight

        # 3. 检查应用是否已知
        if not self._is_known_app(activity.application):
            weight = UNCERTAINTY_SOURCES["unknown_app"]["weight"]
            sources.sources["unknown_app"] = weight
            total += weight

        # 4. 检查活动持续时间
        if activity.duration_seconds < self._min_duration_threshold:
            weight = UNCERTAINTY_SOURCES["short_duration"]["weight"]
            sources.sources["short_duration"] = weight
            total += weight

        sources.total_score = min(1.0, total)
        return sources

    def _is_known_app(self, app_name: str) -> bool:
        """
        检查应用是否在已知列表中

        Args:
            app_name: 应用名称

        Returns:
            是否已知
        """
        app_lower = app_name.lower()
        for known in self._known_apps:
            if known in app_lower:
                return True
        return False

    def _is_generic_title(self, title: str) -> bool:
        """
        检查标题是否为通用标题

        Args:
            title: 窗口标题

        Returns:
            是否为通用标题
        """
        title_lower = title.lower()

        # 完全匹配
        for generic in self._generic_titles:
            if title_lower == generic:
                return True

        # 前缀匹配
        for generic in self._generic_titles:
            if title_lower.startswith(generic):
                return True

        # 检查标题长度（过短的标题信息量低）
        if len(title) < 5:
            return True

        return False

    def _build_reason(self, sources: UncertaintySources) -> str:
        """构建原因说明"""
        if not sources.sources:
            return "无不确定性来源"

        parts = []
        for source_key, weight in sources.sources.items():
            desc = UNCERTAINTY_SOURCES.get(source_key, {}).get("description", source_key)
            parts.append(f"{desc}(+{weight:.2f})")

        return "; ".join(parts)

    def add_known_app(self, app_name: str) -> None:
        """添加已知应用"""
        self._known_apps.add(app_name.lower())

    def add_generic_title(self, title: str) -> None:
        """添加通用标题"""
        self._generic_titles.append(title.lower())

    @property
    def min_duration_threshold(self) -> int:
        """获取最短持续时间阈值"""
        return self._min_duration_threshold

    @min_duration_threshold.setter
    def min_duration_threshold(self, value: int) -> None:
        """设置最短持续时间阈值"""
        self._min_duration_threshold = max(0, value)

    @property
    def known_apps(self) -> set[str]:
        """获取已知应用列表"""
        return self._known_apps.copy()

    @property
    def uncertainty_rate(self) -> float:
        """
        获取高不确定性率

        Returns:
            高不确定性活动占比
        """
        total = (
            self._stats["high_uncertainty_count"] +
            self._stats["low_uncertainty_count"]
        )
        if total == 0:
            return 0.0
        return self._stats["high_uncertainty_count"] / total

    def compute_activity_uncertainty(
        self,
        activity: ActivityEvent,
        has_screenshot: bool = True,
    ) -> float:
        """
        快速计算活动的不确定性分数

        不需要完整分析，仅计算分数

        Args:
            activity: 活动事件
            has_screenshot: 是否有截图

        Returns:
            不确定性分数 (0.0-1.0)
        """
        screenshot = object() if has_screenshot else None
        sources = self._compute_uncertainty_sources(activity, screenshot)
        return sources.total_score
