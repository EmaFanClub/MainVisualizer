"""
黑名单过滤器

强制标记高敏感应用，返回高 TI 分数建议，这些活动必须进行 VLM 分析。
黑名单活动不会被跳过，而是被标记为需要立即处理。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from .base_filter import BaseFilter, FilterResult

if TYPE_CHECKING:
    from src.ingest.manictime.models import ActivityEvent


# 默认黑名单应用程序 - 高敏感度应用
DEFAULT_BLACKLIST_APPS = [
    # 金融应用
    "alipay",
    "wechatpay",
    "taobao",
    "jd",
    "pinduoduo",

    # 银行客户端
    "icbc",       # 工商银行
    "ccb",        # 建设银行
    "boc",        # 中国银行
    "abc",        # 农业银行
    "cmb",        # 招商银行

    # 支付和加密货币
    "paypal",
    "venmo",
    "binance",
    "coinbase",
    "metamask",

    # 隐私工具
    "tor",
    "i2p",
    "1password",
    "bitwarden",
    "keepass",
    "lastpass",
    "dashlane",

    # VPN 和代理
    "expressvpn",
    "nordvpn",
    "surfshark",
    "clash",
    "v2ray",
    "shadowsocks",
]

# 默认黑名单标题关键词
DEFAULT_BLACKLIST_TITLE_KEYWORDS = [
    # 隐私浏览
    "incognito",
    "private browsing",
    "inprivate",
    "隐私模式",
    "无痕",

    # 敏感操作
    "网银",
    "银行卡",
    "信用卡",
    "转账",
    "汇款",
    "password manager",
    "密码管理",

    # 认证相关
    "two-factor",
    "2fa",
    "authenticator",
    "验证码",

    # 加密相关
    "wallet",
    "钱包",
    "crypto",
    "bitcoin",
    "ethereum",
]


@dataclass
class BlacklistMatch:
    """
    黑名单匹配结果

    Attributes:
        matched: 是否匹配
        match_type: 匹配类型 (app/title)
        matched_rule: 匹配的规则
        suggested_ti: 建议的 TI 分数
    """
    matched: bool
    match_type: str = ""
    matched_rule: str = ""
    suggested_ti: float = 0.9


class BlacklistFilter(BaseFilter):
    """
    黑名单过滤器

    检查活动是否在黑名单中，黑名单活动将被标记为高优先级，
    建议立即进行 VLM 分析。

    注意: 这个过滤器与白名单过滤器不同，它不会跳过活动，
    而是标记活动需要特殊处理。通过 FilterResult 的 should_skip=False
    让活动继续流转，但在 matched_rule 中提供建议信息。

    Attributes:
        blacklist_apps: 黑名单应用列表
        blacklist_title_keywords: 黑名单标题关键词列表
        force_immediate: 是否强制立即触发
        suggested_ti_score: 建议的 TI 分数
    """

    def __init__(
        self,
        blacklist_apps: Optional[list[str]] = None,
        blacklist_title_keywords: Optional[list[str]] = None,
        force_immediate: bool = True,
        suggested_ti_score: float = 0.9,
        enabled: bool = True,
    ) -> None:
        """
        初始化黑名单过滤器

        Args:
            blacklist_apps: 黑名单应用列表
            blacklist_title_keywords: 黑名单标题关键词列表
            force_immediate: 是否强制立即触发 VLM 分析
            suggested_ti_score: 建议的 TI 分数
            enabled: 是否启用
        """
        super().__init__(name="blacklist", enabled=enabled)

        # 转换为小写以便不区分大小写匹配
        self._blacklist_apps = set(
            app.lower() for app in (blacklist_apps or DEFAULT_BLACKLIST_APPS)
        )
        self._blacklist_title_keywords = [
            kw.lower() for kw in (
                blacklist_title_keywords or DEFAULT_BLACKLIST_TITLE_KEYWORDS
            )
        ]

        self._force_immediate = force_immediate
        self._suggested_ti_score = max(0.0, min(1.0, suggested_ti_score))

        # 扩展统计
        self._stats.update({
            "blacklist_hits": 0,
            "app_matches": 0,
            "title_matches": 0,
        })

    def _do_check(self, activity: ActivityEvent) -> FilterResult:
        """
        执行黑名单检查

        注意: 黑名单过滤器不会跳过活动(should_skip=False)，
        而是通过 matched_rule 传递建议信息给后续处理阶段。

        Args:
            activity: 活动事件

        Returns:
            FilterResult: 过滤结果
        """
        app_name = activity.application.lower()
        window_title = activity.window_title.lower()

        # 检查应用程序黑名单
        match = self._check_blacklist(app_name, window_title)

        if match.matched:
            self._stats["blacklist_hits"] += 1
            if match.match_type == "app":
                self._stats["app_matches"] += 1
            else:
                self._stats["title_matches"] += 1

            # 返回通过结果，但在 matched_rule 中包含黑名单信息
            # 这样后续处理可以根据这个信息调整 TI 分数
            return FilterResult(
                should_skip=False,
                filter_name=self.name,
                reason=f"黑名单匹配: {match.match_type}:{match.matched_rule}",
                matched_rule=f"blacklist:{match.match_type}:{match.matched_rule}:"
                             f"ti={match.suggested_ti}:immediate={self._force_immediate}",
            )

        return FilterResult.passed(self.name)

    def _check_blacklist(
        self,
        app_name: str,
        window_title: str,
    ) -> BlacklistMatch:
        """
        检查是否命中黑名单

        Args:
            app_name: 应用名称(已转小写)
            window_title: 窗口标题(已转小写)

        Returns:
            BlacklistMatch: 匹配结果
        """
        # 检查应用黑名单
        for blacklist_app in self._blacklist_apps:
            if blacklist_app in app_name:
                return BlacklistMatch(
                    matched=True,
                    match_type="app",
                    matched_rule=blacklist_app,
                    suggested_ti=self._suggested_ti_score,
                )

        # 检查标题关键词
        for keyword in self._blacklist_title_keywords:
            if keyword in window_title:
                return BlacklistMatch(
                    matched=True,
                    match_type="title",
                    matched_rule=keyword,
                    suggested_ti=self._suggested_ti_score,
                )

        return BlacklistMatch(matched=False)

    def is_blacklisted(self, activity: ActivityEvent) -> bool:
        """
        快速检查活动是否在黑名单中

        Args:
            activity: 活动事件

        Returns:
            是否在黑名单中
        """
        app_name = activity.application.lower()
        window_title = activity.window_title.lower()
        match = self._check_blacklist(app_name, window_title)
        return match.matched

    def add_app(self, app_name: str) -> None:
        """添加应用到黑名单"""
        self._blacklist_apps.add(app_name.lower())

    def remove_app(self, app_name: str) -> bool:
        """
        从黑名单移除应用

        Returns:
            是否成功移除
        """
        lower_name = app_name.lower()
        if lower_name in self._blacklist_apps:
            self._blacklist_apps.discard(lower_name)
            return True
        return False

    def add_title_keyword(self, keyword: str) -> None:
        """添加标题关键词到黑名单"""
        self._blacklist_title_keywords.append(keyword.lower())

    @property
    def blacklist_apps(self) -> set[str]:
        """获取黑名单应用列表"""
        return self._blacklist_apps.copy()

    @property
    def blacklist_title_keywords(self) -> list[str]:
        """获取黑名单标题关键词列表"""
        return self._blacklist_title_keywords.copy()

    @property
    def force_immediate(self) -> bool:
        """是否强制立即触发"""
        return self._force_immediate

    @force_immediate.setter
    def force_immediate(self, value: bool) -> None:
        """设置是否强制立即触发"""
        self._force_immediate = value

    @property
    def suggested_ti_score(self) -> float:
        """获取建议的 TI 分数"""
        return self._suggested_ti_score
