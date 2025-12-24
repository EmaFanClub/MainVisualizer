"""
ContextSwitchAnalyzer 单元测试
"""

from datetime import datetime, timedelta

import pytest

from src.senatus.analyzers import ContextSwitchAnalyzer


class TestContextSwitchAnalyzer:
    """上下文切换分析器测试"""

    def test_default_weight(self):
        """测试默认权重"""
        analyzer = ContextSwitchAnalyzer()
        assert analyzer.weight == 0.15

    def test_insufficient_history_low_score(self, make_activity):
        """测试历史不足时低分"""
        analyzer = ContextSwitchAnalyzer()
        activity = make_activity()

        result = analyzer.analyze(activity)

        # 历史不足
        assert result.score <= 0.3
        assert "不足" in result.reason or result.details.get("history_size", 0) < 2

    def test_rapid_switching_high_score(self, make_activity, base_timestamp):
        """测试快速切换高分"""
        analyzer = ContextSwitchAnalyzer(rapid_switch_threshold=5.0)

        # 创建快速切换序列
        apps = ["Code.exe", "Chrome.exe", "Slack.exe", "Code.exe"]
        for i, app in enumerate(apps):
            ts = base_timestamp + timedelta(seconds=i * 2)  # 2秒间隔
            activity = make_activity(
                application=app,
                timestamp=ts,
            )
            result = analyzer.analyze(activity)

        # 最后一次应该检测到快速切换
        assert result.score > 0.4
        patterns = result.details.get("patterns", [])
        pattern_types = [p.get("type") for p in patterns]
        assert "rapid_switch" in pattern_types

    def test_abab_pattern_detection(self, make_activity, base_timestamp):
        """测试 A-B-A-B 模式检测"""
        analyzer = ContextSwitchAnalyzer()

        # 创建 A-B-A-B 模式
        apps = ["Code.exe", "Chrome.exe", "Code.exe", "Chrome.exe"]
        for i, app in enumerate(apps):
            ts = base_timestamp + timedelta(seconds=i * 10)
            activity = make_activity(
                application=app,
                timestamp=ts,
            )
            result = analyzer.analyze(activity)

        # 应该检测到 ABAB 模式
        patterns = result.details.get("patterns", [])
        pattern_types = [p.get("type") for p in patterns]
        assert "abab_comparison" in pattern_types

    def test_deep_to_shallow_switch_cost(self, make_activity, base_timestamp):
        """测试深度工作到浅工作的切换成本"""
        analyzer = ContextSwitchAnalyzer()

        # 从 VSCode(深度工作) 切换到 Discord(浅工作)
        apps = ["dummy1.exe", "dummy2.exe", "Code.exe", "Discord.exe"]
        for i, app in enumerate(apps):
            ts = base_timestamp + timedelta(seconds=i * 10)
            activity = make_activity(
                application=app,
                timestamp=ts,
            )
            result = analyzer.analyze(activity)

        # 应该有切换成本模式
        patterns = result.details.get("patterns", [])
        for p in patterns:
            if p.get("type") == "switch_cost":
                assert p.get("score", 0) >= 0.6

    def test_same_app_no_switch(self, make_activity, base_timestamp):
        """测试同一应用无切换"""
        analyzer = ContextSwitchAnalyzer()

        # 连续使用同一应用
        for i in range(4):
            ts = base_timestamp + timedelta(seconds=i * 10)
            activity = make_activity(
                application="Code.exe",
                timestamp=ts,
            )
            result = analyzer.analyze(activity)

        # 无切换模式
        assert result.score <= 0.3

    def test_set_context_window(self, make_activity, activity_sequence):
        """测试设置上下文窗口"""
        analyzer = ContextSwitchAnalyzer(context_window_size=10)

        # 创建历史活动
        history = activity_sequence(
            apps=["App1.exe", "App2.exe", "App3.exe"],
            interval_seconds=10,
        )

        # 设置上下文
        analyzer.set_context_window(history)

        assert analyzer.current_history_length == 3

    def test_clear_history(self, make_activity):
        """测试清除历史"""
        analyzer = ContextSwitchAnalyzer()

        # 添加一些活动
        for _ in range(3):
            analyzer.analyze(make_activity())

        assert analyzer.current_history_length > 0

        analyzer.clear_history()
        assert analyzer.current_history_length == 0

    def test_disabled_analyzer(self, make_activity):
        """测试禁用分析器"""
        analyzer = ContextSwitchAnalyzer(enabled=False)

        result = analyzer.analyze(make_activity())

        assert result.score == 0.0
        # 禁用时返回 zero 结果

    def test_stats_tracking(self, make_activity, base_timestamp):
        """测试统计跟踪"""
        analyzer = ContextSwitchAnalyzer(rapid_switch_threshold=5.0)

        # 创建一些快速切换
        apps = ["Code.exe", "Chrome.exe", "Slack.exe"]
        for i, app in enumerate(apps):
            ts = base_timestamp + timedelta(seconds=i * 2)
            analyzer.analyze(make_activity(application=app, timestamp=ts))

        stats = analyzer.switch_pattern_stats
        assert "rapid_switches" in stats

    def test_context_window_size_limit(self, make_activity, base_timestamp):
        """测试上下文窗口大小限制"""
        analyzer = ContextSwitchAnalyzer(context_window_size=5)

        # 添加超过限制的活动
        for i in range(10):
            ts = base_timestamp + timedelta(seconds=i * 10)
            analyzer.analyze(make_activity(
                application=f"App{i}.exe",
                timestamp=ts,
            ))

        assert analyzer.current_history_length <= 5

    def test_analyzer_name(self):
        """测试分析器名称"""
        analyzer = ContextSwitchAnalyzer()
        assert analyzer.name == "context_switch"

    def test_enabled_property(self):
        """测试启用属性"""
        analyzer = ContextSwitchAnalyzer(enabled=False)
        assert analyzer.enabled is False

        analyzer.enabled = True
        assert analyzer.enabled is True
