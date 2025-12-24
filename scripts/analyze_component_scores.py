"""
分析器组件分数分布分析

详细分析各个分析器(Analyzer)的评分分布，找出TI分数偏低的原因。
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import setup_logging, get_logger
from src.ingest.manictime import ManicTimeDBConnector, ActivityParser, ScreenshotLoader
from src.senatus import SenatusEngine
from src.senatus.ti_calculator import TabooIndexCalculator
from src.senatus.analyzers import (
    MetadataAnalyzer,
    VisualAnalyzer,
    FrameDiffAnalyzer,
    ContextSwitchAnalyzer,
    UncertaintyAnalyzer,
)

# 配置
DB_PATH = Path(r"D:\code_field\manicData\db\ManicTimeReports.db")
SCREENSHOTS_PATH = Path(r"Y:\临时文件\ManicTimeScreenShots")
SAMPLE_SIZE = 500  # 采样数量

logger = get_logger(__name__)


def analyze_component_distribution(
    activities: list,
    screenshot_loader: ScreenshotLoader = None,
    sample_size: int = SAMPLE_SIZE,
) -> dict:
    """
    分析各组件的分数分布

    Args:
        activities: 活动列表
        screenshot_loader: 截图加载器
        sample_size: 采样大小

    Returns:
        分析结果
    """
    # 初始化各分析器（直接使用，不通过引擎）
    analyzers = [
        MetadataAnalyzer(weight=0.25),
        VisualAnalyzer(weight=0.35),
        ContextSwitchAnalyzer(weight=0.15),
        FrameDiffAnalyzer(weight=0.15),
        UncertaintyAnalyzer(weight=0.10),
    ]

    # 存储各分析器的分数
    component_scores = {a.name: [] for a in analyzers}
    weighted_scores = {a.name: [] for a in analyzers}
    final_ti_scores = []

    # 采样
    sampled = activities[:sample_size]

    for i, activity in enumerate(sampled):
        if (i + 1) % 100 == 0:
            print(f"处理进度: {i + 1}/{len(sampled)}")

        # 加载截图
        screenshot = None
        if screenshot_loader:
            try:
                screenshot = screenshot_loader.load_by_timestamp(
                    activity.timestamp,
                    tolerance_seconds=60,
                )
            except Exception:
                pass

        # 运行各分析器
        total_weighted = 0.0
        total_weight = 0.0

        for analyzer in analyzers:
            result = analyzer.analyze(activity, screenshot)
            component_scores[analyzer.name].append(result.score)
            weighted = result.score * analyzer.weight
            weighted_scores[analyzer.name].append(weighted)
            total_weighted += weighted
            total_weight += analyzer.weight

        # 计算最终TI
        final_ti = total_weighted / total_weight if total_weight > 0 else 0.0
        final_ti_scores.append(final_ti)

    # 统计各分析器
    stats = {}
    for name in component_scores:
        scores = component_scores[name]
        w_scores = weighted_scores[name]

        if scores:
            sorted_scores = sorted(scores)
            n = len(sorted_scores)

            stats[name] = {
                "avg": sum(scores) / n,
                "min": min(scores),
                "max": max(scores),
                "median": sorted_scores[n // 2],
                "p25": sorted_scores[n // 4],
                "p75": sorted_scores[3 * n // 4],
                "p90": sorted_scores[int(0.9 * n)],
                "weighted_avg": sum(w_scores) / n,
                "weight": next(a.weight for a in analyzers if a.name == name),
            }

    return {
        "component_stats": stats,
        "final_ti_stats": {
            "avg": sum(final_ti_scores) / len(final_ti_scores),
            "min": min(final_ti_scores),
            "max": max(final_ti_scores),
            "median": sorted(final_ti_scores)[len(final_ti_scores) // 2],
        },
        "sample_size": len(sampled),
    }


def print_component_report(results: dict) -> None:
    """打印组件分析报告"""
    print("\n" + "=" * 70)
    print("                  分析器组件分数分布报告")
    print("=" * 70)

    print(f"\n采样数量: {results['sample_size']}")

    print(f"\n各分析器分数分布:")
    print("-" * 70)
    print(f"{'分析器':<20} {'权重':<8} {'平均':<8} {'最小':<8} {'最大':<8} {'P90':<8} {'加权贡献':<10}")
    print("-" * 70)

    for name, stats in sorted(results['component_stats'].items()):
        print(
            f"{name:<20} "
            f"{stats['weight']:<8.2f} "
            f"{stats['avg']:<8.4f} "
            f"{stats['min']:<8.4f} "
            f"{stats['max']:<8.4f} "
            f"{stats['p90']:<8.4f} "
            f"{stats['weighted_avg']:<10.4f}"
        )

    print("-" * 70)

    # 最终TI统计
    ti_stats = results['final_ti_stats']
    print(f"\n最终 TI 分数:")
    print(f"  - 平均值: {ti_stats['avg']:.4f}")
    print(f"  - 最小值: {ti_stats['min']:.4f}")
    print(f"  - 最大值: {ti_stats['max']:.4f}")
    print(f"  - 中位数: {ti_stats['median']:.4f}")

    # 分析问题
    print("\n" + "=" * 70)
    print("                        问题分析")
    print("=" * 70)

    # 计算各分析器对最终分数的贡献
    total_contribution = sum(
        stats['weighted_avg'] for stats in results['component_stats'].values()
    )

    print(f"\n各分析器对最终TI的贡献占比:")
    for name, stats in sorted(
        results['component_stats'].items(),
        key=lambda x: x[1]['weighted_avg'],
        reverse=True,
    ):
        pct = stats['weighted_avg'] / total_contribution * 100 if total_contribution > 0 else 0
        print(f"  - {name:<20}: {stats['weighted_avg']:.4f} ({pct:.1f}%)")

    # 识别潜在问题
    print(f"\n潜在问题识别:")
    for name, stats in results['component_stats'].items():
        if stats['max'] < 0.5:
            print(f"  [问题] {name}: 最大分数仅 {stats['max']:.4f}，可能评分偏保守")
        if stats['p90'] < stats['avg'] * 1.3:
            print(f"  [注意] {name}: P90 ({stats['p90']:.4f}) 与平均值接近，分布较集中")

    # 优化建议
    print(f"\n优化建议:")
    print("  1. 阈值调整: 根据实际分布调整 immediate/batch 阈值")
    print("  2. 权重调整: 可考虑提高敏感度高的分析器权重")
    print("  3. 评分公式: 可考虑调整评分上限，扩大高敏感度场景的评分")


def main():
    """主函数"""
    setup_logging()

    print("分析器组件分数分布分析工具")
    print("-" * 40)

    if not DB_PATH.exists():
        print(f"错误: 数据库文件不存在: {DB_PATH}")
        return 1

    # 初始化
    parser = ActivityParser(local_timezone_hours=8)

    screenshot_loader = None
    if SCREENSHOTS_PATH.exists():
        try:
            screenshot_loader = ScreenshotLoader(SCREENSHOTS_PATH)
            print("截图加载器已启用")
        except Exception as e:
            print(f"警告: 无法初始化截图加载器: {e}")

    # 加载数据
    try:
        with ManicTimeDBConnector(DB_PATH) as db:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)

            raw_activities = db.query_activities(start_time, end_time)
            applications = db.query_applications_model()
            app_map = {app.common_id: app for app in applications}

            activities = parser.batch_parse(raw_activities, app_map)
            print(f"加载了 {len(activities)} 条活动记录")

            # 分析
            print(f"\n开始分析组件分数分布...")
            results = analyze_component_distribution(
                activities,
                screenshot_loader,
                sample_size=SAMPLE_SIZE,
            )

            # 打印报告
            print_component_report(results)

    except Exception as e:
        print(f"分析过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
