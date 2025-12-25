"""
验证 BatchImageProcessor 和 VisualAnalyzer 集成功能

临时测试脚本，验证 PyTorch 批量图像处理模块是否正常工作。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.senatus.batch_image_processor import BatchImageProcessor, compute_image_features
from src.senatus.analyzers.visual_analyzer import (
    VisualAnalyzer,
    _BATCH_PROCESSOR_AVAILABLE,
    _compute_image_entropy,
    _estimate_text_density,
)
from PIL import Image
import time


def test_batch_processor():
    """测试批量处理器功能"""
    print("=== BatchImageProcessor 模块验证 ===")

    # 创建测试图像 - 模拟有内容的截图
    img = Image.new('RGB', (800, 600), color='white')
    # 添加一些变化以模拟真实图像
    for x in range(0, 800, 10):
        for y in range(0, 600, 10):
            c = (x * y) % 256
            img.putpixel((x, y), (c, c, c))

    # 创建处理器实例
    processor = BatchImageProcessor()
    print(f"设备: {processor.device}")
    print(f"使用 CUDA: {processor.is_cuda}")

    # 测试单张处理
    start = time.perf_counter()
    features = processor.process_single(img)
    elapsed = time.perf_counter() - start

    print(f"\n单张图像处理时间: {elapsed*1000:.2f}ms")
    print(f"  熵值: {features.entropy:.4f}")
    print(f"  文本密度: {features.text_density:.4f}")
    print(f"  边缘比例: {features.edge_ratio:.4f}")

    # 测试批量处理
    batch_sizes = [10, 32, 50]
    for batch_size in batch_sizes:
        images = [img] * batch_size
        start = time.perf_counter()
        results = processor.process_batch(images)
        elapsed = time.perf_counter() - start
        avg_time = elapsed * 1000 / batch_size
        print(f"\n批量处理 {batch_size} 张: {elapsed*1000:.2f}ms (平均 {avg_time:.2f}ms/张)")

    print("\n=== BatchImageProcessor 测试通过! ===")


def test_visual_analyzer_integration():
    """测试 VisualAnalyzer 与 BatchImageProcessor 集成"""
    print("\n=== VisualAnalyzer 集成验证 ===")
    print(f"批量处理器可用: {_BATCH_PROCESSOR_AVAILABLE}")

    # 创建测试图像
    img = Image.new('RGB', (1920, 1080), color='white')
    for x in range(0, 1920, 20):
        for y in range(0, 1080, 20):
            c = ((x * y) % 256, (x + y) % 256, (x - y) % 256)
            img.putpixel((x, y), c)

    # 测试纯 Python 实现
    start = time.perf_counter()
    entropy_py = _compute_image_entropy(img)
    text_density_py = _estimate_text_density(img)
    elapsed_py = time.perf_counter() - start
    print(f"\n纯 Python 实现: {elapsed_py*1000:.2f}ms")
    print(f"  熵值: {entropy_py:.4f}")
    print(f"  文本密度: {text_density_py:.4f}")

    # 测试 VisualAnalyzer (使用批量处理器)
    analyzer_fast = VisualAnalyzer(use_batch_processor=True)
    start = time.perf_counter()
    result_fast = analyzer_fast.analyze_image_only(img)
    elapsed_fast = time.perf_counter() - start
    print(f"\nVisualAnalyzer (PyTorch): {elapsed_fast*1000:.2f}ms")
    print(f"  熵值: {result_fast['entropy']:.4f}")
    print(f"  文本密度: {result_fast['text_density']:.4f}")

    # 测试 VisualAnalyzer (不使用批量处理器)
    analyzer_slow = VisualAnalyzer(use_batch_processor=False)
    start = time.perf_counter()
    result_slow = analyzer_slow.analyze_image_only(img)
    elapsed_slow = time.perf_counter() - start
    print(f"\nVisualAnalyzer (Python): {elapsed_slow*1000:.2f}ms")
    print(f"  熵值: {result_slow['entropy']:.4f}")
    print(f"  文本密度: {result_slow['text_density']:.4f}")

    # 性能对比
    speedup = elapsed_slow / elapsed_fast if elapsed_fast > 0 else 0
    print(f"\n性能提升: {speedup:.1f}x")

    print("\n=== VisualAnalyzer 集成测试通过! ===")


if __name__ == "__main__":
    test_batch_processor()
    test_visual_analyzer_integration()
