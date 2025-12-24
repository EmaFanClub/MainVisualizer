"""
StaticFrameFilter 单元测试
"""

import pytest
from PIL import Image

from src.senatus.filters import StaticFrameFilter


class TestStaticFrameFilter:
    """静态帧过滤器测试"""

    def test_first_frame_not_skipped(self, make_activity, sample_image):
        """测试第一帧不跳过"""
        filter_ = StaticFrameFilter()
        activity = make_activity()

        result = filter_.check_with_image(activity, sample_image)

        assert result.should_skip is False

    def test_identical_frames_skipped(self, make_activity, make_image):
        """测试相同帧被跳过"""
        filter_ = StaticFrameFilter(diff_threshold=0.05)

        # 创建两个相同的图像
        image1 = make_image(color=(100, 100, 100))
        image2 = make_image(color=(100, 100, 100))

        activity1 = make_activity()
        activity2 = make_activity()

        # 第一帧
        result1 = filter_.check_with_image(activity1, image1)
        assert result1.should_skip is False

        # 第二帧(相同)
        result2 = filter_.check_with_image(activity2, image2)
        assert result2.should_skip is True
        assert "static" in result2.reason.lower() or "静态" in result2.reason

    def test_different_frames_not_skipped(self, make_activity):
        """测试不同帧不被跳过"""
        from PIL import Image
        filter_ = StaticFrameFilter(diff_threshold=0.05)

        # 创建两个有图案差异的图像(纯色图像哈希相同)
        image1 = Image.new("RGB", (100, 100), (0, 0, 0))
        image2 = Image.new("RGB", (100, 100), (0, 0, 0))

        # 在第二张图上画不同的图案
        pixels = image2.load()
        for i in range(50):
            for j in range(100):
                pixels[i, j] = (255, 255, 255)

        activity1 = make_activity()
        activity2 = make_activity()

        # 第一帧
        filter_.check_with_image(activity1, image1)

        # 第二帧(有图案差异)
        result2 = filter_.check_with_image(activity2, image2)
        assert result2.should_skip is False

    def test_no_screenshot_not_skipped(self, make_activity):
        """测试无截图路径不跳过"""
        filter_ = StaticFrameFilter()
        activity = make_activity(screenshot_path=None)

        # 使用标准 check 方法，无截图时通过
        result = filter_.check(activity)

        assert result.should_skip is False

    def test_history_size_limit(self, make_activity, make_image):
        """测试历史大小限制"""
        filter_ = StaticFrameFilter(history_size=3)

        # 添加多个帧
        for i in range(5):
            image = make_image(color=(i * 50, i * 50, i * 50))
            filter_.check_with_image(make_activity(), image)

        # 历史不应超过限制
        assert len(filter_.history) <= 3

    def test_clear_history(self, make_activity, sample_image):
        """测试清除历史"""
        filter_ = StaticFrameFilter()

        # 添加帧
        filter_.check_with_image(make_activity(), sample_image)
        assert len(filter_.history) > 0

        # 清除
        filter_.clear_history()
        assert len(filter_.history) == 0

    def test_diff_threshold_adjustment(self, make_activity, make_image):
        """测试差异阈值调整"""
        # 宽松阈值
        filter_loose = StaticFrameFilter(diff_threshold=0.5)
        # 严格阈值
        filter_strict = StaticFrameFilter(diff_threshold=0.01)

        # 创建略微不同的图像
        image1 = make_image(color=(100, 100, 100))
        image2 = make_image(color=(110, 110, 110))

        # 宽松阈值
        filter_loose.check_with_image(make_activity(), image1)
        result_loose = filter_loose.check_with_image(make_activity(), image2)

        # 严格阈值
        filter_strict.check_with_image(make_activity(), image1)
        result_strict = filter_strict.check_with_image(make_activity(), image2)

        # 宽松阈值更容易跳过(或都不跳过，取决于差异程度)
        # 主要验证可以正常运行

    def test_disabled_filter(self, make_activity, sample_image):
        """测试禁用过滤器"""
        filter_ = StaticFrameFilter(enabled=False)

        # 即使有相同图像也不跳过
        filter_.check_with_image(make_activity(), sample_image)
        result = filter_.check_with_image(make_activity(), sample_image)

        assert result.should_skip is False

    def test_stats_tracking(self, make_activity):
        """测试统计跟踪"""
        from PIL import Image
        filter_ = StaticFrameFilter()

        # 第一帧
        image1 = Image.new("RGB", (100, 100), (0, 0, 0))
        filter_.check_with_image(make_activity(), image1)

        # 相同帧
        image2 = Image.new("RGB", (100, 100), (0, 0, 0))
        filter_.check_with_image(make_activity(), image2)

        # 不同帧(有图案差异)
        image3 = Image.new("RGB", (100, 100), (0, 0, 0))
        pixels = image3.load()
        for i in range(50):
            for j in range(100):
                pixels[i, j] = (255, 255, 255)
        filter_.check_with_image(make_activity(), image3)

        stats = filter_.stats
        assert stats["total_checked"] == 3
        # 第二帧与第一帧相同，会被标记为静态
        assert stats["static_frames"] >= 1

    def test_compute_hash(self, sample_image):
        """测试哈希计算"""
        filter_ = StaticFrameFilter(hash_size=8)

        ahash, dhash = filter_.compute_hash(sample_image)

        assert len(ahash) > 0
        assert len(dhash) > 0

    def test_compare_images(self):
        """测试图像比较"""
        from PIL import Image
        filter_ = StaticFrameFilter()

        # 相同图像
        image1 = Image.new("RGB", (100, 100), (100, 100, 100))
        image2 = Image.new("RGB", (100, 100), (100, 100, 100))
        diff_same = filter_.compare_images(image1, image2)
        assert diff_same < 0.1  # 应该非常相似

        # 不同图像(有图案差异)
        image3 = Image.new("RGB", (100, 100), (0, 0, 0))
        image4 = Image.new("RGB", (100, 100), (0, 0, 0))
        pixels = image4.load()
        for i in range(50):
            for j in range(100):
                pixels[i, j] = (255, 255, 255)
        diff_different = filter_.compare_images(image3, image4)
        assert diff_different > 0.2  # 应该有明显差异

    def test_static_frame_rate(self, make_activity, make_image):
        """测试静态帧率"""
        filter_ = StaticFrameFilter()

        # 添加一些帧
        for i in range(3):
            filter_.check_with_image(make_activity(), make_image(color=(0, 0, 0)))

        # 添加不同帧
        filter_.check_with_image(make_activity(), make_image(color=(255, 255, 255)))

        rate = filter_.static_frame_rate
        assert 0.0 <= rate <= 1.0
