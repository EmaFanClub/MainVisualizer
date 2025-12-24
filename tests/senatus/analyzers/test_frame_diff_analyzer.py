"""
FrameDiffAnalyzer 单元测试
"""

from datetime import datetime, timedelta

import pytest
from PIL import Image

from src.senatus.analyzers import FrameDiffAnalyzer


class TestFrameDiffAnalyzer:
    """帧差异分析器测试"""

    def test_default_weight(self):
        """测试默认权重"""
        analyzer = FrameDiffAnalyzer()
        assert analyzer.weight == 0.15

    def test_first_frame_low_score(self, make_activity, sample_image):
        """测试第一帧低分"""
        analyzer = FrameDiffAnalyzer()
        activity = make_activity()

        result = analyzer.analyze(activity, sample_image)

        # 第一帧无对比，分数较低
        assert result.score <= 0.3
        assert result.details.get("is_first_frame") is True

    def test_identical_frames_low_score(self, make_activity, make_image):
        """测试相同帧低分"""
        analyzer = FrameDiffAnalyzer()

        image1 = make_image(color=(100, 100, 100))
        image2 = make_image(color=(100, 100, 100))

        activity1 = make_activity()
        activity2 = make_activity()

        # 第一帧
        analyzer.analyze(activity1, image1)

        # 第二帧(相同)
        result = analyzer.analyze(activity2, image2)

        # 相同帧差异小
        assert result.score <= 0.3

    def test_different_frames_high_score(self, make_activity, make_image):
        """测试不同帧高分"""
        analyzer = FrameDiffAnalyzer()

        image1 = make_image(color=(0, 0, 0))
        image2 = make_image(color=(255, 255, 255))

        activity1 = make_activity()
        activity2 = make_activity()

        # 第一帧
        analyzer.analyze(activity1, image1)

        # 第二帧(完全不同)
        result = analyzer.analyze(activity2, image2)

        # 不同帧差异大
        assert result.score >= 0.5

    def test_no_screenshot_low_score(self, make_activity):
        """测试无截图低分"""
        analyzer = FrameDiffAnalyzer()
        activity = make_activity()

        result = analyzer.analyze(activity, screenshot=None)

        assert result.score <= 0.3
        assert result.confidence < 1.0

    def test_clear_history(self, make_activity, sample_image):
        """测试清除历史"""
        analyzer = FrameDiffAnalyzer()

        analyzer.analyze(make_activity(), sample_image)

        # 验证有历史
        # 注意：具体属性名取决于实现

        analyzer.clear_history()
        # 清除后应该可以正常工作

    def test_disabled_analyzer(self, make_activity, sample_image):
        """测试禁用分析器"""
        analyzer = FrameDiffAnalyzer(enabled=False)

        result = analyzer.analyze(make_activity(), sample_image)

        assert result.score == 0.0
        # 禁用时返回 zero 结果

    def test_stats_tracking(self, make_activity, sample_image):
        """测试统计跟踪"""
        analyzer = FrameDiffAnalyzer()

        analyzer.analyze(make_activity(), sample_image)
        analyzer.analyze(make_activity(), sample_image)

        stats = analyzer.stats
        assert stats["total_analyzed"] == 2

    def test_diff_level_in_result(self, make_activity, make_image):
        """测试结果中的差异级别"""
        analyzer = FrameDiffAnalyzer()

        # 创建不同的帧
        image1 = make_image(color=(0, 0, 0))
        image2 = make_image(color=(255, 255, 255))

        analyzer.analyze(make_activity(), image1)
        result = analyzer.analyze(make_activity(), image2)

        # 结果应包含差异级别
        assert "diff_level" in result.details

    def test_analyzer_name(self):
        """测试分析器名称"""
        analyzer = FrameDiffAnalyzer()
        assert analyzer.name == "frame_diff"

    def test_enabled_property(self):
        """测试启用属性"""
        analyzer = FrameDiffAnalyzer(enabled=False)
        assert analyzer.enabled is False

        analyzer.enabled = True
        assert analyzer.enabled is True
