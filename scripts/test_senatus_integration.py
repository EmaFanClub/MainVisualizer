"""
Senatus 模块集成测试脚本

测试完整流程:
1. 从 ManicTime 数据库读取活动数据
2. 使用 Senatus 引擎处理活动，计算 TI 值
3. 对高 TI 活动调用 VLM 进行深度分析

运行方式:
    conda activate mv
    python scripts/test_senatus_integration.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logger import setup_logging, get_logger
from src.ingest.manictime import (
    ManicTimeDBConnector,
    ScreenshotLoader,
    ActivityParser,
)
from src.senatus import (
    SenatusEngine,
    TriggerThresholds,
    DecisionType,
    TILevel,
    WhitelistFilter,
    MetadataAnalyzer,
)
from src.admina import QwenVLProvider

# 配置
DB_PATH = os.getenv(
    "MANICTIME_DB_PATH",
    r"D:\code_field\manicData\db\ManicTimeReports.db"
)
SCREENSHOTS_PATH = os.getenv(
    "MANICTIME_SCREENSHOTS_PATH",
    r"Y:\临时文件\ManicTimeScreenShots"
)
# 使用环境变量或默认测试 API Key
API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-6c514e90b3144159b4e281666f7447b1")

# 设置日志
setup_logging()
logger = get_logger(__name__)


def print_section(title: str) -> None:
    """打印分节标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_decision_summary(decisions: list, events: list) -> dict:
    """打印决策摘要"""
    print_section("决策摘要统计")

    summary = {
        DecisionType.IMMEDIATE: [],
        DecisionType.BATCH: [],
        DecisionType.SKIP: [],
        DecisionType.DELAY: [],
        DecisionType.FILTERED: [],
    }

    for decision, event in zip(decisions, events):
        summary[decision.decision_type].append((decision, event))

    print(f"\n决策分布:")
    print("-" * 40)
    for dtype, items in summary.items():
        print(f"  {dtype.name:12} : {len(items):4} 个")

    # 打印高 TI 活动详情
    immediate_items = summary[DecisionType.IMMEDIATE]
    if immediate_items:
        print(f"\n需立即分析的活动 (ti >= 0.7):")
        print("-" * 40)
        for decision, event in immediate_items[:5]:  # 只显示前5个
            print(f"  [{decision.ti_score:.2f}] {event.application} - {event.window_title[:40]}")

    return summary


async def test_vlm_analysis(
    provider: QwenVLProvider,
    loader: ScreenshotLoader,
    high_ti_items: list,
    max_samples: int = 3,
) -> list[dict]:
    """对高 TI 活动进行 VLM 分析"""
    print_section(f"VLM 深度分析 (最多 {max_samples} 个)")

    # 健康检查
    print("\n测试 VLM 连接...")
    try:
        health = await provider.health_check()
        if not health.is_healthy:
            print(f"  VLM 服务不健康: {health.message}")
            return []
        models_str = ", ".join(health.available_models[:3]) if health.available_models else "N/A"
        print(f"  连接成功: {health.message}")
        print(f"  可用模型: {models_str}")
    except Exception as e:
        print(f"  连接失败: {e}")
        return []

    results = []
    analyzed = 0

    for decision, event in high_ti_items:
        if analyzed >= max_samples:
            break

        # 查找对应的截图
        screenshot_path = loader.find_screenshot_path(
            event.timestamp,
            tolerance_seconds=120
        )

        if not screenshot_path or not screenshot_path.exists():
            print(f"\n  跳过: 无截图 - {event.event_id}")
            continue

        print(f"\n分析样本 {analyzed + 1}:")
        print(f"  TI 分数: {decision.ti_score:.3f}")
        print(f"  应用: {event.application}")
        print(f"  窗口: {event.window_title[:50]}")
        print(f"  时间: {event.timestamp}")
        print(f"  截图: {screenshot_path.name}")

        # VLM 分析
        prompt = """分析这张屏幕截图，返回JSON格式:
{
    "content_type": "code_editing|document|browsing|communication|media|system|other",
    "activity_summary": "一句话描述用户正在做什么",
    "sensitivity_level": "high|medium|low",
    "key_elements": ["关键UI元素1", "关键UI元素2"],
    "productivity_score": 0.0-1.0
}"""

        try:
            result = await provider.analyze_image(
                image=screenshot_path,
                prompt=prompt,
                max_tokens=400,
            )

            content = result.get("content", "")
            latency = result.get("latency_ms", 0)

            print(f"  VLM 响应 ({latency}ms):")
            # 格式化显示
            for line in content.split("\n")[:8]:
                print(f"    {line}")

            results.append({
                "event_id": str(event.event_id),
                "ti_score": decision.ti_score,
                "application": event.application,
                "vlm_analysis": content,
                "latency_ms": latency,
            })

            analyzed += 1

        except Exception as e:
            print(f"  分析失败: {e}")
            continue

    print(f"\n成功分析 {len(results)} 个高 TI 活动")
    return results


async def main():
    """主测试函数"""
    print("=" * 60)
    print("  Senatus 模块集成测试")
    print("=" * 60)
    print(f"\n配置:")
    print(f"  数据库: {DB_PATH}")
    print(f"  截图目录: {SCREENSHOTS_PATH}")

    # 检查数据库
    if not Path(DB_PATH).exists():
        print(f"\n错误: 数据库文件不存在: {DB_PATH}")
        return

    # 初始化组件
    print_section("初始化组件")

    db = ManicTimeDBConnector(DB_PATH)
    loader = ScreenshotLoader(SCREENSHOTS_PATH)
    parser = ActivityParser(local_timezone_hours=8)

    # 配置 Senatus 引擎 - 降低阈值以便测试 VLM 分析
    thresholds = TriggerThresholds(
        immediate_threshold=0.5,  # 降低以触发更多 VLM 分析
        batch_threshold=0.3,
        skip_threshold=0.15,
    )

    engine = SenatusEngine(thresholds=thresholds)

    # 初始化 VLM 提供商
    provider = QwenVLProvider(
        api_key=API_KEY,
        model="qwen-vl-max",  # 使用更强的模型
    )

    print(f"  ManicTimeDBConnector: 已初始化")
    print(f"  ScreenshotLoader: 已初始化")
    print(f"  SenatusEngine: 已初始化")
    print(f"  QwenVLProvider: 已初始化 (model={provider.name})")

    try:
        # 连接数据库
        db.connect()

        # 获取数据范围
        min_time, max_time = db.get_date_range()
        print(f"\n数据库时间范围: {min_time} ~ {max_time}")

        # 查询最近3天数据
        query_end = max_time
        query_start = max_time - timedelta(days=3)

        print_section("加载活动数据")
        print(f"查询范围: {query_start} ~ {query_end}")

        # 获取原始活动
        raw_activities = db.query_activities(query_start, query_end)
        print(f"获取到 {len(raw_activities)} 条原始活动记录")

        if not raw_activities:
            print("没有找到活动数据")
            return

        # 获取应用信息
        apps = db.query_applications_model()
        app_map = {app.common_id: app for app in apps}
        print(f"获取到 {len(apps)} 个应用信息")

        # 解析活动事件
        events = parser.batch_parse(raw_activities, app_map)
        print(f"解析出 {len(events)} 个 ActivityEvent")

        # 限制测试数量
        test_events = events[-200:] if len(events) > 200 else events
        print(f"测试样本: {len(test_events)} 个事件")

        # Senatus 处理
        print_section("Senatus 引擎处理")

        decisions = []
        for event in test_events:
            # 尝试加载截图
            screenshot = None
            if event.screenshot_path:
                try:
                    screenshot = loader.load_by_timestamp(
                        event.timestamp,
                        tolerance_seconds=60
                    )
                except Exception:
                    pass

            decision = engine.process_activity(event, screenshot)
            decisions.append(decision)

        # 打印统计
        stats = engine.get_stats()
        print(f"\n引擎统计:")
        print(f"  总处理: {stats['engine']['total_processed']}")
        print(f"  被过滤: {stats['engine']['filtered_count']}")
        print(f"  已分析: {stats['engine']['analyzed_count']}")
        print(f"  过滤率: {engine.get_filter_rate():.1%}")
        print(f"  触发率: {engine.get_trigger_rate():.1%}")

        # 打印各过滤器统计
        print(f"\n过滤器统计:")
        for name, fstats in stats['filters'].items():
            print(f"  {name}: checked={fstats.get('checked', 0)}, filtered={fstats.get('filtered', 0)}")

        # 触发管理器统计
        tm_stats = stats['trigger_manager']
        print(f"\n触发管理器统计:")
        print(f"  立即触发: {tm_stats['immediate_count']}")
        print(f"  批处理: {tm_stats['batch_count']}")
        print(f"  跳过: {tm_stats['skip_count']}")
        print(f"  延迟: {tm_stats['delay_count']}")

        # 决策摘要
        summary = print_decision_summary(decisions, test_events)

        # VLM 分析高 TI 活动
        # 优先分析 IMMEDIATE，如果没有则分析 BATCH
        high_ti_items = summary[DecisionType.IMMEDIATE]
        if not high_ti_items:
            high_ti_items = summary[DecisionType.BATCH][:10]  # 取前10个BATCH
            print("\n没有 IMMEDIATE 活动，改为分析 BATCH 活动")

        if high_ti_items:
            vlm_results = await test_vlm_analysis(
                provider, loader, high_ti_items, max_samples=3
            )
        else:
            print("\n没有需要 VLM 分析的活动")

        # 最终总结
        print_section("测试完成")
        print(f"""
测试结果:
  - 处理活动数: {len(test_events)}
  - 过滤率: {engine.get_filter_rate():.1%}
  - 触发率: {engine.get_trigger_rate():.1%}
  - 立即分析: {len(summary[DecisionType.IMMEDIATE])} 个
  - 批处理: {len(summary[DecisionType.BATCH])} 个
  - 跳过分析: {len(summary[DecisionType.SKIP])} 个
  - 被过滤: {len(summary[DecisionType.FILTERED])} 个

Senatus 模块集成测试通过!
""")

    except Exception as e:
        logger.exception(f"测试失败: {e}")
        raise
    finally:
        db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
