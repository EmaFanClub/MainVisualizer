"""
白名单过滤器

过滤白名单中的应用程序活动，这些活动被认为是安全的，不需要 VLM 分析。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from .base_filter import BaseFilter, FilterResult

if TYPE_CHECKING:
    from src.ingest.manictime.models import ActivityEvent


# 默认白名单应用程序
DEFAULT_WHITELIST_APPS = [
    # 开发工具 - 常规编码活动
    "code.exe",
    "devenv.exe",
    "idea64.exe",
    "pycharm64.exe",
    "webstorm64.exe",
    "rider64.exe",

    # 终端
    "windowsterminal.exe",
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",

    # 系统工具
    "explorer.exe",
    "taskmgr.exe",
    "mmc.exe",

    # 办公软件 - 常规使用
    "winword.exe",
    "excel.exe",
    "powerpnt.exe",
    "outlook.exe",

    # 通讯工具
    "teams.exe",
    "slack.exe",
    "zoom.exe",

    # 笔记工具
    "obsidian.exe",
    "notion.exe",
    "onenote.exe",
]

# 默认白名单窗口标题关键词
DEFAULT_WHITELIST_TITLE_KEYWORDS = [
    # 开发相关
    "visual studio",
    "debug",
    "terminal",

    # 系统界面
    "settings",
    "control panel",
]


class WhitelistFilter(BaseFilter):
    """
    白名单过滤器

    检查活动是否在白名单中，白名单活动将被跳过 VLM 分析。

    Attributes:
        whitelist_apps: 白名单应用列表(小写)
        whitelist_title_keywords: 白名单标题关键词列表(小写)
        use_regex: 是否使用正则表达式匹配
    """

    def __init__(
        self,
        whitelist_apps: Optional[list[str]] = None,
        whitelist_title_keywords: Optional[list[str]] = None,
        use_regex: bool = False,
        enabled: bool = True,
    ) -> None:
        """
        初始化白名单过滤器

        Args:
            whitelist_apps: 白名单应用列表
            whitelist_title_keywords: 白名单标题关键词列表
            use_regex: 是否使用正则表达式匹配
            enabled: 是否启用
        """
        super().__init__(name="whitelist", enabled=enabled)

        # 转换为小写以便不区分大小写匹配
        self._whitelist_apps = set(
            app.lower() for app in (whitelist_apps or DEFAULT_WHITELIST_APPS)
        )
        self._whitelist_title_keywords = [
            kw.lower() for kw in (
                whitelist_title_keywords or DEFAULT_WHITELIST_TITLE_KEYWORDS
            )
        ]
        self._use_regex = use_regex

        # 预编译正则表达式
        if self._use_regex:
            self._app_patterns = [
                re.compile(app, re.IGNORECASE) for app in self._whitelist_apps
            ]
            self._title_patterns = [
                re.compile(kw, re.IGNORECASE)
                for kw in self._whitelist_title_keywords
            ]

    def _do_check(self, activity: ActivityEvent) -> FilterResult:
        """
        执行白名单检查

        Args:
            activity: 活动事件

        Returns:
            FilterResult: 过滤结果
        """
        app_name = activity.application.lower()
        window_title = activity.window_title.lower()

        # 检查应用程序白名单
        if self._check_app_whitelist(app_name):
            return FilterResult.skipped(
                filter_name=self.name,
                reason=f"应用 {activity.application} 在白名单中",
                matched_rule=f"app:{activity.application}",
            )

        # 检查窗口标题关键词
        matched_keyword = self._check_title_keywords(window_title)
        if matched_keyword:
            return FilterResult.skipped(
                filter_name=self.name,
                reason=f"窗口标题包含白名单关键词: {matched_keyword}",
                matched_rule=f"title:{matched_keyword}",
            )

        return FilterResult.passed(self.name)

    def _check_app_whitelist(self, app_name: str) -> bool:
        """检查应用是否在白名单中"""
        if self._use_regex:
            return any(p.search(app_name) for p in self._app_patterns)
        return app_name in self._whitelist_apps

    def _check_title_keywords(self, title: str) -> Optional[str]:
        """检查标题是否包含白名单关键词"""
        if self._use_regex:
            for pattern in self._title_patterns:
                if pattern.search(title):
                    return pattern.pattern
            return None

        for keyword in self._whitelist_title_keywords:
            if keyword in title:
                return keyword
        return None

    def add_app(self, app_name: str) -> None:
        """添加应用到白名单"""
        self._whitelist_apps.add(app_name.lower())
        if self._use_regex:
            self._app_patterns.append(re.compile(app_name, re.IGNORECASE))

    def remove_app(self, app_name: str) -> None:
        """从白名单移除应用"""
        self._whitelist_apps.discard(app_name.lower())

    def add_title_keyword(self, keyword: str) -> None:
        """添加标题关键词到白名单"""
        self._whitelist_title_keywords.append(keyword.lower())
        if self._use_regex:
            self._title_patterns.append(re.compile(keyword, re.IGNORECASE))

    @property
    def whitelist_apps(self) -> set[str]:
        """获取白名单应用列表"""
        return self._whitelist_apps.copy()

    @property
    def whitelist_title_keywords(self) -> list[str]:
        """获取白名单标题关键词列表"""
        return self._whitelist_title_keywords.copy()
