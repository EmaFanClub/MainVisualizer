"""
UncertaintyAnalyzer 单元测试
"""

import pytest

from src.senatus.analyzers import UncertaintyAnalyzer


class TestUncertaintyAnalyzer:
    """不确定性分析器测试"""

    def test_default_weight(self):
        """测试默认权重"""
        analyzer = UncertaintyAnalyzer()
        assert analyzer.weight == 0.10

    def test_no_screenshot_adds_uncertainty(self, make_activity):
        """测试无截图增加不确定性"""
        analyzer = UncertaintyAnalyzer()
        activity = make_activity()

        result = analyzer.analyze(activity, screenshot=None)

        # 无截图应该增加不确定性
        sources = result.details.get("sources", {})
        assert "no_screenshot" in sources
        assert result.score > 0.2

    def test_empty_title_adds_uncertainty(self, make_activity):
        """测试空标题增加不确定性"""
        analyzer = UncertaintyAnalyzer()
        activity = make_activity(window_title="")

        result = analyzer.analyze(activity)

        sources = result.details.get("sources", {})
        assert "empty_title" in sources

    def test_unknown_app_adds_uncertainty(self, make_activity):
        """测试未知应用增加不确定性"""
        analyzer = UncertaintyAnalyzer()
        activity = make_activity(application="RandomUnknownApp.exe")

        result = analyzer.analyze(activity)

        sources = result.details.get("sources", {})
        assert "unknown_app" in sources

    def test_short_duration_adds_uncertainty(self, make_activity):
        """测试短持续时间增加不确定性"""
        analyzer = UncertaintyAnalyzer(min_duration_threshold=10)
        activity = make_activity(duration_seconds=3)

        result = analyzer.analyze(activity)

        sources = result.details.get("sources", {})
        assert "short_duration" in sources

    def test_generic_title_adds_uncertainty(self, make_activity):
        """测试通用标题增加不确定性"""
        analyzer = UncertaintyAnalyzer()
        activity = make_activity(window_title="Untitled")

        result = analyzer.analyze(activity)

        sources = result.details.get("sources", {})
        assert "generic_title" in sources

    def test_known_app_no_uncertainty(self, make_activity, sample_image):
        """测试已知应用无应用不确定性"""
        analyzer = UncertaintyAnalyzer()
        activity = make_activity(
            application="Code.exe",
            window_title="main.py - Visual Studio Code",
            duration_seconds=60,
        )

        result = analyzer.analyze(activity, sample_image)

        sources = result.details.get("sources", {})
        assert "unknown_app" not in sources

    def test_multiple_uncertainty_sources(self, make_activity):
        """测试多个不确定性来源"""
        analyzer = UncertaintyAnalyzer()
        activity = make_activity(
            application="UnknownApp.exe",
            window_title="",
            duration_seconds=2,
        )

        result = analyzer.analyze(activity, screenshot=None)

        sources = result.details.get("sources", {})
        # 应该有多个来源
        assert len(sources) >= 3

    def test_uncertainty_score_capped(self, make_activity):
        """测试不确定性分数上限"""
        analyzer = UncertaintyAnalyzer()
        activity = make_activity(
            application="UnknownApp.exe",
            window_title="",
            duration_seconds=1,
        )

        result = analyzer.analyze(activity, screenshot=None)

        # 分数应该被限制在 1.0
        assert result.score <= 1.0

    def test_add_known_app(self, make_activity):
        """测试添加已知应用"""
        analyzer = UncertaintyAnalyzer()

        # 初始为未知
        activity1 = make_activity(application="MyCustomApp.exe")
        result1 = analyzer.analyze(activity1)
        assert "unknown_app" in result1.details.get("sources", {})

        # 添加到已知列表
        analyzer.add_known_app("mycustomapp")

        # 现在应该是已知
        result2 = analyzer.analyze(activity1)
        assert "unknown_app" not in result2.details.get("sources", {})

    def test_add_generic_title(self, make_activity):
        """测试添加通用标题"""
        analyzer = UncertaintyAnalyzer()

        # 初始不是通用标题
        activity = make_activity(window_title="CustomPlaceholder")
        result1 = analyzer.analyze(activity)
        assert "generic_title" not in result1.details.get("sources", {})

        # 添加到通用标题列表
        analyzer.add_generic_title("customplaceholder")

        # 现在应该是通用标题
        result2 = analyzer.analyze(activity)
        assert "generic_title" in result2.details.get("sources", {})

    def test_disabled_analyzer(self, make_activity):
        """测试禁用分析器"""
        analyzer = UncertaintyAnalyzer(enabled=False)

        result = analyzer.analyze(make_activity())

        assert result.score == 0.0
        # 禁用时返回 zero 结果

    def test_stats_tracking(self, make_activity, sample_image):
        """测试统计跟踪"""
        analyzer = UncertaintyAnalyzer()

        # 高不确定性
        analyzer.analyze(make_activity(
            application="Unknown.exe",
            window_title="",
        ))

        # 低不确定性
        analyzer.analyze(make_activity(
            application="Code.exe",
            window_title="main.py",
        ), sample_image)

        stats = analyzer.stats
        assert stats["high_uncertainty_count"] >= 1

    def test_uncertainty_rate(self, make_activity, sample_image):
        """测试不确定性率"""
        analyzer = UncertaintyAnalyzer()

        # 创建一些高低不确定性的活动
        for _ in range(2):
            analyzer.analyze(make_activity(
                application="Unknown.exe",
                window_title="",
            ))

        for _ in range(3):
            analyzer.analyze(make_activity(
                application="Code.exe",
                window_title="main.py",
            ), sample_image)

        rate = analyzer.uncertainty_rate
        assert 0.0 <= rate <= 1.0

    def test_quick_uncertainty_computation(self, make_activity):
        """测试快速不确定性计算"""
        analyzer = UncertaintyAnalyzer()
        activity = make_activity(
            application="Unknown.exe",
            window_title="",
        )

        score = analyzer.compute_activity_uncertainty(activity, has_screenshot=False)

        assert score > 0.3

    def test_analyzer_name(self):
        """测试分析器名称"""
        analyzer = UncertaintyAnalyzer()
        assert analyzer.name == "uncertainty"

    def test_enabled_property(self):
        """测试启用属性"""
        analyzer = UncertaintyAnalyzer(enabled=False)
        assert analyzer.enabled is False

        analyzer.enabled = True
        assert analyzer.enabled is True
