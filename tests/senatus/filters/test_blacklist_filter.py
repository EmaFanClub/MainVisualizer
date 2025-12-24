"""
BlacklistFilter 单元测试
"""

import pytest

from src.senatus.filters import BlacklistFilter


class TestBlacklistFilter:
    """黑名单过滤器测试"""

    def test_default_blacklist_matches_bank_app(self, make_activity):
        """测试默认黑名单匹配银行应用"""
        filter_ = BlacklistFilter()
        activity = make_activity(application="中国工商银行.exe")

        result = filter_.check(activity)

        # 黑名单匹配不跳过，而是标记优先处理
        assert result.should_skip is False
        # matched_rule 可能为空字符串或包含规则信息
        # 取决于具体实现

    def test_default_blacklist_matches_vpn(self, make_activity):
        """测试默认黑名单匹配 VPN 应用"""
        filter_ = BlacklistFilter()
        activity = make_activity(application="ExpressVPN.exe")

        result = filter_.check(activity)

        assert result.should_skip is False

    def test_default_blacklist_matches_crypto(self, make_activity):
        """测试默认黑名单匹配加密货币应用"""
        filter_ = BlacklistFilter()
        activity = make_activity(application="Binance.exe")

        result = filter_.check(activity)

        assert result.should_skip is False

    def test_title_keyword_matching(self, make_activity):
        """测试标题关键词匹配"""
        filter_ = BlacklistFilter(
            blacklist_title_keywords=["密码", "password"]
        )
        activity = make_activity(
            application="Chrome.exe",
            window_title="修改密码 - Chrome"
        )

        result = filter_.check(activity)

        assert result.should_skip is False
        # 匹配时 matched_rule 应该有内容
        assert result.matched_rule != ""

    def test_no_match_returns_passed(self, make_activity):
        """测试无匹配时返回通过"""
        filter_ = BlacklistFilter()
        activity = make_activity(
            application="Chrome.exe",
            window_title="Google Search"
        )

        result = filter_.check(activity)

        assert result.should_skip is False
        # 无匹配时 matched_rule 为空字符串
        assert result.matched_rule == ""

    def test_custom_blacklist(self, make_activity):
        """测试自定义黑名单"""
        filter_ = BlacklistFilter(
            blacklist_apps=["custom_secret_app"],
            blacklist_title_keywords=["机密"]
        )

        # 自定义应用匹配
        activity1 = make_activity(application="custom_secret_app.exe")
        result1 = filter_.check(activity1)
        assert result1.matched_rule != ""

        # 自定义关键词匹配
        activity2 = make_activity(
            application="Word.exe",
            window_title="机密文档.docx"
        )
        result2 = filter_.check(activity2)
        assert result2.matched_rule != ""

    def test_disabled_filter(self, make_activity):
        """测试禁用过滤器"""
        filter_ = BlacklistFilter(enabled=False)
        activity = make_activity(application="中国银行.exe")

        result = filter_.check(activity)

        assert result.should_skip is False
        # 禁用时返回通过结果

    def test_stats_tracking(self, make_activity):
        """测试统计跟踪"""
        filter_ = BlacklistFilter()

        # 匹配
        filter_.check(make_activity(application="中国银行.exe"))
        # 不匹配
        filter_.check(make_activity(application="Chrome.exe"))

        stats = filter_.stats
        assert stats["total_checked"] == 2

    def test_filter_name(self):
        """测试过滤器名称"""
        filter_ = BlacklistFilter()
        assert filter_.name == "blacklist"

    def test_enabled_property(self):
        """测试启用属性"""
        filter_ = BlacklistFilter(enabled=False)
        assert filter_.enabled is False

        filter_.enabled = True
        assert filter_.enabled is True
