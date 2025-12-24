"""
TI 分布分析脚本

从 ManicTime 数据库读取真实活动数据，计算 TI 分布情况，
用于验证和调优阈值设置。
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import setup_logging, get_logger
from src.core.exceptions import DatabaseConnectionError
from src.ingest.manictime import ManicTimeDBConnector, ActivityParser, ScreenshotLoader
from src.senatus import SenatusEngine, DecisionType
from src.senatus.models import TILevel

# 配置
DB_PATH = Path(r"D:\code_field\manicData\db\ManicTimeReports.db")
SCREENSHOTS_PATH = Path(r"Y:\临时文件\ManicTimeScreenShots")
MIN_ACTIVITIES = 1000  # 最小测试数据量

logger = get_logger(__name__)


def load_activities(
    db: ManicTimeDBConnector,
    parser: ActivityParser,
    days: int = 7,
) -> list:
    """
    加载活动数据

    Args:
        db: 数据库连接器
        parser: 活动解析器
        days: 回溯天数

    Returns:
        ActivityEvent 列表
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    # 获取原始数据
    raw_activities = db.query_activities(start_time, end_time)
    applications = db.query_applications_model()

    # 创建应用映射
    app_map = {app.common_id: app for app in applications}

    # 解析为 ActivityEvent
    events = parser.batch_parse(raw_activities, app_map)

    logger.info(f"加载了 {len(events)} 条活动记录 (过去 {days} 天)")
    return events


def analyze_ti_distribution(
    engine: SenatusEngine,
    activities: list,
    screenshot_loader: Optional[ScreenshotLoader] = None,
) -> dict:
    """
    分析 TI 分布

    Args:
        engine: Senatus 引擎
        activities: 活动列表
        screenshot_loader: 截图加载器(可选)

    Returns:
        分析结果字典
    """
    ti_scores = []
    ti_levels = Counter()
    decision_types = Counter()
    app_ti_scores = defaultdict(list)
    component_scores = defaultdict(list)
    filtered_count = 0

    total = len(activities)

    for i, activity in enumerate(activities):
        if (i + 1) % 200 == 0:
            logger.info(f"处理进度: {i + 1}/{total}")

        # 尝试加载截图
        screenshot = None
        if screenshot_loader:
            try:
                screenshot = screenshot_loader.load_by_timestamp(
                    activity.timestamp,
                    tolerance_seconds=60,
                )
            except Exception:
                pass

        # 处理活动
        decision = engine.process_activity(activity, screenshot)

        # 记录决策类型
        decision_types[decision.decision_type.value] += 1

        # 如果被过滤，跳过详细统计
        if decision.decision_type == DecisionType.FILTERED:
            filtered_count += 1
            continue

        # 记录 TI 分数
        ti_score = decision.ti_score
        ti_scores.append(ti_score)

        # 记录级别分布
        if ti_score > 0.7:
            ti_levels["HIGH"] += 1
        elif ti_score > 0.4:
            ti_levels["MEDIUM"] += 1
        elif ti_score > 0.2:
            ti_levels["LOW"] += 1
        else:
            ti_levels["MINIMAL"] += 1

        # 按应用统计
        app_name = activity.application.lower()
        app_ti_scores[app_name].append(ti_score)

    # 计算统计数据
    if ti_scores:
        avg_ti = sum(ti_scores) / len(ti_scores)
        sorted_scores = sorted(ti_scores)
        median_ti = sorted_scores[len(sorted_scores) // 2]

        # 分位数
        p25_idx = len(sorted_scores) // 4
        p75_idx = 3 * len(sorted_scores) // 4
        p90_idx = int(0.9 * len(sorted_scores))
        p95_idx = int(0.95 * len(sorted_scores))

        percentiles = {
            "p25": sorted_scores[p25_idx],
            "p50": median_ti,
            "p75": sorted_scores[p75_idx],
            "p90": sorted_scores[p90_idx] if p90_idx < len(sorted_scores) else sorted_scores[-1],
            "p95": sorted_scores[p95_idx] if p95_idx < len(sorted_scores) else sorted_scores[-1],
        }
    else:
        avg_ti = 0.0
        median_ti = 0.0
        percentiles = {}

    # 按应用计算平均 TI
    app_avg_ti = {}
    for app, scores in app_ti_scores.items():
        if len(scores) >= 10:  # 只统计样本量足够的应用
            app_avg_ti[app] = sum(scores) / len(scores)

    # 排序获取 Top 应用
    top_high_ti_apps = sorted(
        app_avg_ti.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:15]

    top_low_ti_apps = sorted(
        app_avg_ti.items(),
        key=lambda x: x[1],
    )[:15]

    return {
        "total_activities": total,
        "analyzed_count": len(ti_scores),
        "filtered_count": filtered_count,
        "filter_rate": filtered_count / total if total > 0 else 0.0,
        "avg_ti": avg_ti,
        "median_ti": median_ti,
        "min_ti": min(ti_scores) if ti_scores else 0.0,
        "max_ti": max(ti_scores) if ti_scores else 0.0,
        "percentiles": percentiles,
        "ti_levels": dict(ti_levels),
        "decision_types": dict(decision_types),
        "top_high_ti_apps": top_high_ti_apps,
        "top_low_ti_apps": top_low_ti_apps,
        "engine_stats": engine.get_stats(),
    }


def print_report(results: dict) -> None:
    """打印分析报告"""
    print("\n" + "=" * 70)
    print("                      TI 分布分析报告")
    print("=" * 70)

    print(f"\n总体统计:")
    print(f"  - 总活动数: {results['total_activities']}")
    print(f"  - 已分析数: {results['analyzed_count']}")
    print(f"  - 被过滤数: {results['filtered_count']}")
    print(f"  - 过滤率: {results['filter_rate']:.2%}")

    print(f"\nTI 分数分布:")
    print(f"  - 平均值: {results['avg_ti']:.4f}")
    print(f"  - 中位数: {results['median_ti']:.4f}")
    print(f"  - 最小值: {results['min_ti']:.4f}")
    print(f"  - 最大值: {results['max_ti']:.4f}")

    if results['percentiles']:
        print(f"\n分位数:")
        for key, value in results['percentiles'].items():
            print(f"  - {key}: {value:.4f}")

    print(f"\nTI 级别分布:")
    total_analyzed = results['analyzed_count']
    for level, count in sorted(results['ti_levels'].items()):
        pct = count / total_analyzed * 100 if total_analyzed > 0 else 0
        print(f"  - {level}: {count} ({pct:.1f}%)")

    print(f"\n决策类型分布:")
    total = results['total_activities']
    for dtype, count in sorted(results['decision_types'].items()):
        pct = count / total * 100 if total > 0 else 0
        print(f"  - {dtype}: {count} ({pct:.1f}%)")

    print(f"\n高 TI 应用 (Top 15):")
    for app, score in results['top_high_ti_apps']:
        print(f"  - {app[:40]:<40} : {score:.4f}")

    print(f"\n低 TI 应用 (Top 15):")
    for app, score in results['top_low_ti_apps']:
        print(f"  - {app[:40]:<40} : {score:.4f}")

    # 阈值建议
    print("\n" + "=" * 70)
    print("                        阈值优化建议")
    print("=" * 70)

    if results['percentiles']:
        p = results['percentiles']

        print(f"\n当前阈值配置:")
        print(f"  - immediate_threshold: 0.7 (高于此值立即触发 VLM)")
        print(f"  - batch_threshold: 0.4 (0.4-0.7 批处理触发)")
        print(f"  - skip_threshold: 0.2 (低于此值跳过)")

        # 计算各区间占比
        immediate_pct = results['ti_levels'].get('HIGH', 0) / total_analyzed * 100 if total_analyzed > 0 else 0
        batch_pct = results['ti_levels'].get('MEDIUM', 0) / total_analyzed * 100 if total_analyzed > 0 else 0
        skip_pct = (results['ti_levels'].get('LOW', 0) + results['ti_levels'].get('MINIMAL', 0)) / total_analyzed * 100 if total_analyzed > 0 else 0

        print(f"\n基于数据的区间占比:")
        print(f"  - IMMEDIATE (ti > 0.7): {immediate_pct:.1f}%")
        print(f"  - BATCH (0.4 < ti <= 0.7): {batch_pct:.1f}%")
        print(f"  - SKIP (ti <= 0.4): {skip_pct:.1f}%")

        # 基于 P90/P75 建议新阈值
        print(f"\n建议阈值 (基于分位数):")
        print(f"  - immediate_threshold: {p['p90']:.2f} (P90, 约触发 {100-90:.0f}% 活动)")
        print(f"  - batch_threshold: {p['p75']:.2f} (P75, 约触发 {100-75:.0f}% 活动)")
        print(f"  - skip_threshold: {p['p25']:.2f} (P25)")

    print("\n" + "=" * 70)


def main():
    """主函数"""
    setup_logging()

    print("TI 分布分析工具")
    print("-" * 40)

    # 检查数据库
    if not DB_PATH.exists():
        print(f"错误: 数据库文件不存在: {DB_PATH}")
        return 1

    print(f"数据库路径: {DB_PATH}")
    print(f"截图路径: {SCREENSHOTS_PATH}")

    # 初始化组件
    parser = ActivityParser(local_timezone_hours=8)
    engine = SenatusEngine()

    # 截图加载器
    screenshot_loader = None
    if SCREENSHOTS_PATH.exists():
        try:
            screenshot_loader = ScreenshotLoader(SCREENSHOTS_PATH)
            print(f"截图加载器已启用")
        except Exception as e:
            print(f"警告: 无法初始化截图加载器: {e}")
    else:
        print(f"警告: 截图路径不存在，将不加载截图")

    # 连接数据库并加载数据
    try:
        with ManicTimeDBConnector(DB_PATH) as db:
            # 获取数据范围
            min_time, max_time = db.get_date_range()
            total_count = db.get_activity_count()

            print(f"\n数据库信息:")
            print(f"  - 时间范围: {min_time} ~ {max_time}")
            print(f"  - 总记录数: {total_count}")

            # 计算需要回溯的天数以获取足够数据
            days = 7
            while True:
                activities = load_activities(db, parser, days=days)
                if len(activities) >= MIN_ACTIVITIES or days >= 90:
                    break
                days += 7
                print(f"数据不足 {MIN_ACTIVITIES} 条，扩展到 {days} 天")

            if len(activities) < MIN_ACTIVITIES:
                print(f"警告: 仅获取到 {len(activities)} 条活动，少于目标 {MIN_ACTIVITIES} 条")

            # 分析 TI 分布
            print(f"\n开始分析 TI 分布...")
            results = analyze_ti_distribution(engine, activities, screenshot_loader)

            # 打印报告
            print_report(results)

    except DatabaseConnectionError as e:
        print(f"数据库连接错误: {e}")
        return 1
    except Exception as e:
        print(f"分析过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
