"""
元数据分析器

基于活动元数据(应用名称、窗口标题等)分析敏感度。
采用规则匹配方式，无需模型推理。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from .base_analyzer import BaseAnalyzer, AnalyzerResult

if TYPE_CHECKING:
    from PIL import Image
    from src.ingest.manictime.models import ActivityEvent


# 高敏感度应用程序模式
HIGH_SENSITIVITY_APP_PATTERNS = [
    # 浏览器 - 可能访问敏感网站
    r"chrome\.exe",
    r"firefox\.exe",
    r"msedge\.exe",
    r"brave\.exe",
    r"opera\.exe",

    # 社交和即时通讯
    r"telegram\.exe",
    r"discord\.exe",
    r"wechat\.exe",
    r"qq\.exe",
    r"whatsapp\.exe",

    # 文件管理器 - 可能浏览敏感文件
    r"totalcmd\.exe",
    r"everything\.exe",

    # 远程桌面
    r"mstsc\.exe",
    r"anydesk\.exe",
    r"teamviewer\.exe",
]

# 高敏感度标题关键词
HIGH_SENSITIVITY_TITLE_KEYWORDS = [
    # 隐私相关
    "private",
    "incognito",
    "secret",
    "confidential",

    # 账户相关
    "login",
    "password",
    "account",
    "sign in",
    "credential",

    # 敏感内容
    "bank",
    "payment",
    "wallet",
    "crypto",

    # 社交媒体
    "twitter",
    "facebook",
    "instagram",
    "reddit",
    "youtube",

    # 娱乐
    "netflix",
    "spotify",
    "steam",
    "game",
]

# 中等敏感度应用程序模式
MEDIUM_SENSITIVITY_APP_PATTERNS = [
    # 邮件客户端
    r"outlook\.exe",
    r"thunderbird\.exe",

    # 文档工具(可能包含敏感信息)
    r"winword\.exe",
    r"excel\.exe",
    r"acrobat\.exe",
    r"foxitreader\.exe",
]

# 低敏感度应用程序 - 不太可能包含敏感内容
LOW_SENSITIVITY_APP_PATTERNS = [
    # 开发工具
    r"code\.exe",
    r"devenv\.exe",
    r"idea64\.exe",

    # 终端
    r"windowsterminal\.exe",
    r"cmd\.exe",
    r"powershell\.exe",

    # 系统工具
    r"explorer\.exe",
    r"taskmgr\.exe",
]


class MetadataAnalyzer(BaseAnalyzer):
    """
    元数据分析器

    基于应用名称和窗口标题分析活动敏感度

    Attributes:
        high_app_patterns: 高敏感度应用模式(已编译)
        medium_app_patterns: 中敏感度应用模式(已编译)
        low_app_patterns: 低敏感度应用模式(已编译)
        high_title_keywords: 高敏感度标题关键词
    """

    def __init__(
        self,
        weight: float = 0.35,
        enabled: bool = True,
        custom_high_apps: Optional[list[str]] = None,
        custom_high_keywords: Optional[list[str]] = None,
    ) -> None:
        """
        初始化元数据分析器

        Args:
            weight: 权重
            enabled: 是否启用
            custom_high_apps: 自定义高敏感度应用模式
            custom_high_keywords: 自定义高敏感度关键词
        """
        super().__init__(name="metadata", weight=weight, enabled=enabled)

        # 编译正则表达式
        high_patterns = HIGH_SENSITIVITY_APP_PATTERNS.copy()
        if custom_high_apps:
            high_patterns.extend(custom_high_apps)

        self._high_app_patterns = [
            re.compile(p, re.IGNORECASE) for p in high_patterns
        ]
        self._medium_app_patterns = [
            re.compile(p, re.IGNORECASE) for p in MEDIUM_SENSITIVITY_APP_PATTERNS
        ]
        self._low_app_patterns = [
            re.compile(p, re.IGNORECASE) for p in LOW_SENSITIVITY_APP_PATTERNS
        ]

        # 标题关键词
        self._high_title_keywords = [
            kw.lower() for kw in HIGH_SENSITIVITY_TITLE_KEYWORDS
        ]
        if custom_high_keywords:
            self._high_title_keywords.extend(kw.lower() for kw in custom_high_keywords)

    def _do_analyze(
        self,
        activity: ActivityEvent,
        screenshot: Optional[Image.Image] = None,
    ) -> AnalyzerResult:
        """
        执行元数据分析

        Args:
            activity: 活动事件
            screenshot: 关联截图(未使用)

        Returns:
            AnalyzerResult: 分析结果
        """
        app_name = activity.application
        window_title = activity.window_title.lower()

        # 检查应用敏感度
        app_score, app_reason = self._check_app_sensitivity(app_name)

        # 检查标题敏感度
        title_score, title_reason = self._check_title_sensitivity(window_title)

        # 综合评分 - 取较高者
        if app_score >= title_score:
            final_score = app_score
            final_reason = app_reason
        else:
            final_score = title_score
            final_reason = title_reason

        # 两者都有贡献时，略微提高分数
        if app_score > 0 and title_score > 0:
            bonus = min(0.1, (app_score + title_score) * 0.1)
            final_score = min(1.0, final_score + bonus)
            final_reason = f"{app_reason}; {title_reason}"

        return AnalyzerResult(
            analyzer_name=self.name,
            score=final_score,
            confidence=0.9,  # 规则匹配置信度固定
            reason=final_reason,
            details={
                "app_score": app_score,
                "title_score": title_score,
                "app_name": app_name,
                "window_title": activity.window_title,
            },
        )

    def _check_app_sensitivity(self, app_name: str) -> tuple[float, str]:
        """
        检查应用敏感度

        Returns:
            (分数, 原因) 元组
        """
        # 检查高敏感度
        for pattern in self._high_app_patterns:
            if pattern.search(app_name):
                return 0.8, f"高敏感度应用: {app_name}"

        # 检查中敏感度
        for pattern in self._medium_app_patterns:
            if pattern.search(app_name):
                return 0.5, f"中敏感度应用: {app_name}"

        # 检查低敏感度
        for pattern in self._low_app_patterns:
            if pattern.search(app_name):
                return 0.1, f"低敏感度应用: {app_name}"

        # 未知应用 - 给予中等分数
        return 0.4, f"未分类应用: {app_name}"

    def _check_title_sensitivity(self, title: str) -> tuple[float, str]:
        """
        检查标题敏感度

        Returns:
            (分数, 原因) 元组
        """
        matched_keywords = []

        for keyword in self._high_title_keywords:
            if keyword in title:
                matched_keywords.append(keyword)

        if not matched_keywords:
            return 0.0, ""

        # 根据匹配数量计算分数
        base_score = 0.6
        if len(matched_keywords) >= 3:
            score = 0.9
        elif len(matched_keywords) >= 2:
            score = 0.75
        else:
            score = base_score

        keywords_str = ", ".join(matched_keywords[:3])
        return score, f"标题包含敏感关键词: {keywords_str}"

    def add_high_sensitivity_app(self, pattern: str) -> None:
        """添加高敏感度应用模式"""
        self._high_app_patterns.append(re.compile(pattern, re.IGNORECASE))

    def add_high_sensitivity_keyword(self, keyword: str) -> None:
        """添加高敏感度标题关键词"""
        self._high_title_keywords.append(keyword.lower())
