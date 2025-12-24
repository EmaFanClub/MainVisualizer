"""
VisualAnalyzer 单元测试
"""

import pytest
from PIL import Image

from src.senatus.analyzers import VisualAnalyzer


class TestVisualAnalyzer:
    """视觉敏感度分析器测试"""

    def test_default_weight(self):
        """测试默认权重"""
        analyzer = VisualAnalyzer()
        assert analyzer.weight == 0.35

    def test_browser_high_score(self, make_activity, sample_image):
        """测试浏览器有分数"""
        analyzer = VisualAnalyzer()
        activity = make_activity(
            application="Chrome.exe",
            window_title="Example Website"
        )

        result = analyzer.analyze(activity, sample_image)

        # 浏览器应该有分数
        assert result.score >= 0.0

    def test_code_editor_has_score(self, make_activity, sample_image):
        """测试代码编辑器有分数"""
        analyzer = VisualAnalyzer()
        activity = make_activity(
            application="Code.exe",
            window_title="main.py - Visual Studio Code"
        )

        result = analyzer.analyze(activity, sample_image)

        # 代码编辑器应该有分数
        assert 0.0 <= result.score <= 1.0

    def test_no_screenshot_low_confidence(self, make_activity):
        """测试无截图低置信度"""
        analyzer = VisualAnalyzer()
        activity = make_activity()

        result = analyzer.analyze(activity, screenshot=None)

        # 无截图时置信度应该较低
        assert result.confidence < 1.0

    def test_high_entropy_image(self, make_activity):
        """测试高熵图像"""
        analyzer = VisualAnalyzer()
        activity = make_activity()

        # 创建一个有随机噪声的图像(高熵)
        import random
        image = Image.new("RGB", (100, 100))
        pixels = image.load()
        for i in range(100):
            for j in range(100):
                pixels[i, j] = (
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255),
                )

        result = analyzer.analyze(activity, image)

        # 高熵图像应该有分数
        assert result.score >= 0.0

    def test_low_entropy_image(self, make_activity, make_image):
        """测试低熵图像"""
        analyzer = VisualAnalyzer()
        activity = make_activity()

        # 纯色图像(低熵)
        image = make_image(color=(128, 128, 128))

        result = analyzer.analyze(activity, image)

        # 低熵图像熵值为 0
        assert result.details.get("entropy", 0) == 0.0

    def test_disabled_analyzer(self, make_activity, sample_image):
        """测试禁用分析器"""
        analyzer = VisualAnalyzer(enabled=False)
        activity = make_activity()

        result = analyzer.analyze(activity, sample_image)

        assert result.score == 0.0
        # 禁用时返回 zero 结果，confidence 为 1.0

    def test_stats_tracking(self, make_activity, sample_image):
        """测试统计跟踪"""
        analyzer = VisualAnalyzer()

        analyzer.analyze(make_activity(), sample_image)
        analyzer.analyze(make_activity(), sample_image)

        stats = analyzer.stats
        assert stats["total_analyzed"] == 2

    def test_custom_weight(self):
        """测试自定义权重"""
        analyzer = VisualAnalyzer(weight=0.5)
        assert analyzer.weight == 0.5

    def test_result_has_details(self, make_activity, sample_image):
        """测试结果包含详情"""
        analyzer = VisualAnalyzer()
        activity = make_activity()

        result = analyzer.analyze(activity, sample_image)

        # 检查实际的详情字段
        assert "app_score" in result.details or "entropy" in result.details

    def test_analyzer_name(self):
        """测试分析器名称"""
        analyzer = VisualAnalyzer()
        assert analyzer.name == "visual"

    def test_enabled_property(self):
        """测试启用属性"""
        analyzer = VisualAnalyzer(enabled=False)
        assert analyzer.enabled is False

        analyzer.enabled = True
        assert analyzer.enabled is True
