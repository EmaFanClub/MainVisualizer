"""
VLM 分析脚本

分析指定时间范围的电脑使用记录，对高TI活动调用VLM进行深度分析。
支持灵活配置时间范围、阈值和VLM调用限制。

用法:
    python test_vlm_analysis.py [小时数] [--threshold 阈值] [--max-vlm 数量]

示例:
    python test_vlm_analysis.py 168           # 分析7天(168小时)
    python test_vlm_analysis.py 24 --threshold 0.45  # 降低阈值
    python test_vlm_analysis.py 168 --max-vlm 0      # 不限制VLM调用次数
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.core import setup_logging, get_logger
from src.ingest.manictime import ManicTimeDBConnector, ActivityParser, ScreenshotLoader
from src.senatus import SenatusEngine, DecisionType
from src.senatus.trigger_manager import TriggerThresholds
from src.admina.providers.qwen_provider import QwenVLProvider

# 路径配置
DB_PATH = Path(r"D:\code_field\manicData\db\ManicTimeReports.db")
SCREENSHOTS_PATH = Path(r"Y:\临时文件\ManicTimeScreenShots")
OUTPUT_DIR = PROJECT_ROOT / "data" / "vlm_analysis"

# 默认配置
DEFAULT_LOOKBACK_HOURS = 24
DEFAULT_IMMEDIATE_THRESHOLD = 0.55  # 默认立即触发阈值
DEFAULT_BATCH_THRESHOLD = 0.45      # 默认批处理阈值
DEFAULT_MAX_VLM_CALLS = 50          # 默认最大VLM调用次数，0表示不限制

# VLM分析提示词
ANALYSIS_PROMPT = """请对这张电脑屏幕截图进行深度分析。

## 分析步骤

### 1. 界面识别
- 识别当前打开的主要应用程序/网站
- 描述界面布局和可见的UI元素

### 2. 活动内容分析
- 用户正在进行什么具体任务（如编写代码、浏览网页、编辑文档、观看视频等）
- 如果有文本内容，概述其主题或关键信息
- 如果有代码，说明编程语言和大致功能

### 3. 工作上下文推断
- 基于截图内容推断用户的工作/学习领域
- 判断当前活动的性质：专注工作、信息检索、休闲娱乐、沟通交流等
- 评估活动的专注程度和生产力水平

### 4. 关键细节提取
- 提取截图中有价值的关键词、标题、项目名称等
- 如果有多个窗口，描述窗口间的关联性

请用中文回答，以清晰的段落形式组织输出。"""

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="VLM 分析脚本 - 分析电脑使用记录"
    )
    parser.add_argument(
        "hours",
        type=int,
        nargs="?",
        default=DEFAULT_LOOKBACK_HOURS,
        help=f"回溯小时数 (默认: {DEFAULT_LOOKBACK_HOURS})"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=DEFAULT_IMMEDIATE_THRESHOLD,
        help=f"立即触发阈值 (默认: {DEFAULT_IMMEDIATE_THRESHOLD})"
    )
    parser.add_argument(
        "--batch-threshold", "-b",
        type=float,
        default=DEFAULT_BATCH_THRESHOLD,
        help=f"批处理阈值 (默认: {DEFAULT_BATCH_THRESHOLD})"
    )
    parser.add_argument(
        "--max-vlm", "-m",
        type=int,
        default=DEFAULT_MAX_VLM_CALLS,
        help=f"最大VLM调用次数，0表示不限制 (默认: {DEFAULT_MAX_VLM_CALLS})"
    )
    parser.add_argument(
        "--include-batch",
        action="store_true",
        help="同时对BATCH类型活动进行VLM分析"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="减少输出信息"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅分析TI并保存结果，不执行VLM分析"
    )
    return parser.parse_args()


async def analyze_with_vlm(
    provider: QwenVLProvider,
    screenshot_path: Path,
    activity_info: str,
) -> dict:
    """
    使用VLM分析截图

    Args:
        provider: VLM提供商
        screenshot_path: 截图路径
        activity_info: 活动信息

    Returns:
        分析结果字典
    """
    try:
        result = await provider.analyze_image(
            image=screenshot_path,
            prompt=ANALYSIS_PROMPT,
            max_tokens=1024,
            temperature=0.3,
        )
        return {
            "success": True,
            "content": result.get("content", ""),
            "usage": result.get("usage", {}),
            "latency_ms": result.get("latency_ms", 0),
        }
    except Exception as e:
        logger.error(f"VLM分析失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def main():
    """主函数"""
    args = parse_args()
    setup_logging()

    hours = args.hours
    immediate_threshold = args.threshold
    batch_threshold = args.batch_threshold
    max_vlm_calls = args.max_vlm
    include_batch = args.include_batch
    quiet = args.quiet
    dry_run = args.dry_run

    # 计算天数用于显示
    days = hours / 24

    print("=" * 60)
    if days >= 1:
        print(f"       VLM 分析 - 最近 {days:.1f} 天 ({hours}小时)")
    else:
        print(f"       VLM 分析 - 最近 {hours} 小时")
    if dry_run:
        print("       [DRY-RUN 模式 - 仅统计不执行VLM]")
    print("=" * 60)
    print(f"配置: 阈值={immediate_threshold}, 批处理阈值={batch_threshold}")
    print(f"      最大VLM调用={'不限制' if max_vlm_calls == 0 else max_vlm_calls}")
    print(f"      包含BATCH类型: {'是' if include_batch else '否'}")

    # 检查数据库
    if not DB_PATH.exists():
        print(f"错误: 数据库文件不存在: {DB_PATH}")
        return 1

    # 初始化组件，使用自定义阈值
    parser = ActivityParser(local_timezone_hours=8)
    thresholds = TriggerThresholds(
        immediate_threshold=immediate_threshold,
        batch_threshold=batch_threshold,
        skip_threshold=0.30,  # 保持较低的跳过阈值
    )
    engine = SenatusEngine(thresholds=thresholds)

    # 初始化VLM提供商 (dry-run模式跳过)
    vlm_provider = None
    provider_name = None

    if not dry_run:
        print("\n尝试连接VLM服务...")
        try:
            qwen = QwenVLProvider()
            health = await qwen.health_check()
            if health.is_healthy:
                vlm_provider = qwen
                provider_name = "Qwen VL (DashScope)"
                print(f"  Qwen VL: 正常 (延迟: {health.latency_ms:.0f}ms)")
            else:
                print(f"  Qwen VL: 不可用 - {health.message}")
        except Exception as e:
            print(f"  Qwen VL: 不可用 - {e}")

        if vlm_provider is None:
            print("\n错误: Qwen VL服务不可用")
            print("请确保环境变量 DASHSCOPE_API_KEY 已正确设置")
            return 1

        print(f"\n使用VLM提供商: {provider_name}")
    else:
        print("\n[DRY-RUN] 跳过VLM服务连接")

    # 截图加载器
    screenshot_loader = None
    if SCREENSHOTS_PATH.exists():
        try:
            screenshot_loader = ScreenshotLoader(SCREENSHOTS_PATH)
            print(f"截图加载器: 已启用 ({screenshot_loader.get_screenshot_count()} 张截图)")
        except Exception as e:
            print(f"警告: 无法初始化截图加载器: {e}")

    # 加载活动数据
    try:
        with ManicTimeDBConnector(DB_PATH) as db:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            print(f"\n时间范围: {start_time.strftime('%Y-%m-%d %H:%M')} ~ "
                  f"{end_time.strftime('%Y-%m-%d %H:%M')}")

            # 计时: 数据库查询
            t0 = time.time()
            raw_activities = db.query_activities(start_time, end_time)
            t1 = time.time()
            print(f"[计时] 数据库查询: {t1-t0:.2f}s")

            applications = db.query_applications_model()
            app_map = {app.common_id: app for app in applications}

            # 计时: 解析活动
            t2 = time.time()
            activities = parser.batch_parse(raw_activities, app_map)
            t3 = time.time()
            print(f"[计时] 解析活动: {t3-t2:.2f}s")
            print(f"加载活动数: {len(activities)}")

            if not activities:
                print("没有找到指定时间范围的活动记录")
                return 0

            # 分析每个活动
            if not quiet:
                print("\n" + "-" * 60)
                print("活动分析结果:")
                print("-" * 60)

            results = []
            vlm_count = 0
            vlm_queue = []  # VLM分析队列

            # 计时: TI分析
            ti_start = time.time()
            screenshot_time = 0.0
            ti_calc_time = 0.0

            # 第一遍：收集所有活动的TI决策
            for i, activity in enumerate(activities):
                # 加载截图
                screenshot = None
                screenshot_path = None
                ss_t0 = time.time()
                if screenshot_loader:
                    try:
                        screenshot_path = screenshot_loader.find_screenshot_path(
                            activity.timestamp,
                            tolerance_seconds=60,
                        )
                        if screenshot_path:
                            screenshot = screenshot_loader.load_by_timestamp(
                                activity.timestamp,
                                tolerance_seconds=60,
                            )
                    except Exception:
                        pass
                screenshot_time += time.time() - ss_t0

                # 计算TI
                ti_t0 = time.time()
                decision = engine.process_activity(activity, screenshot)
                ti_calc_time += time.time() - ti_t0

                result = {
                    "index": i + 1,
                    "timestamp": activity.timestamp.strftime("%H:%M:%S"),
                    "date": activity.timestamp.strftime("%Y-%m-%d"),
                    "application": activity.application,
                    "window_title": activity.window_title[:80] if activity.window_title else "",
                    "duration": activity.duration_seconds,
                    "ti_score": decision.ti_score,
                    "decision": decision.decision_type.value,
                    "has_screenshot": screenshot_path is not None,
                    "vlm_analysis": None,
                }

                # 判断是否需要VLM分析
                needs_vlm = False
                if screenshot_path:
                    if decision.decision_type == DecisionType.IMMEDIATE:
                        needs_vlm = True
                    elif include_batch and decision.decision_type == DecisionType.BATCH:
                        needs_vlm = True

                if needs_vlm:
                    vlm_queue.append((i, result, screenshot_path, activity))

                results.append(result)

                # 进度显示 (每 50 条或最后一条)
                if not quiet and ((i + 1) % 50 == 0 or i == len(activities) - 1):
                    elapsed = time.time() - ti_start
                    speed = (i + 1) / elapsed if elapsed > 0 else 0
                    remaining = (len(activities) - i - 1) / speed if speed > 0 else 0
                    print(f"\r  进度: {i + 1}/{len(activities)} "
                          f"({(i + 1) / len(activities) * 100:.1f}%) "
                          f"[{elapsed:.1f}s, {speed:.1f}条/秒, 剩余~{remaining:.0f}s]    ",
                          end="", flush=True)

            if not quiet:
                print()  # 换行

            ti_end = time.time()
            print(f"\n[计时] TI分析总耗时: {ti_end-ti_start:.2f}s")
            print(f"  - 截图加载: {screenshot_time:.2f}s")
            print(f"  - TI计算: {ti_calc_time:.2f}s")
            print(f"\n需要VLM分析的活动: {len(vlm_queue)} 条")

            # 第二遍：执行VLM分析 (dry-run模式跳过)
            if vlm_queue and not dry_run:
                # 限制VLM调用次数
                if max_vlm_calls > 0 and len(vlm_queue) > max_vlm_calls:
                    print(f"限制VLM调用次数为 {max_vlm_calls}")
                    vlm_queue = vlm_queue[:max_vlm_calls]

                print(f"开始VLM分析...")
                for idx, (i, result, screenshot_path, activity) in enumerate(vlm_queue):
                    if not quiet:
                        print(f"\n[{idx + 1}/{len(vlm_queue)}] "
                              f"{result['date']} {result['timestamp']} | "
                              f"TI={result['ti_score']:.3f}")
                        print(f"    应用: {activity.application}")
                        title_preview = activity.window_title[:60] if activity.window_title else '(无)'
                        print(f"    标题: {title_preview}")

                    vlm_result = await analyze_with_vlm(
                        vlm_provider,
                        screenshot_path,
                        f"{activity.application}: {activity.window_title}",
                    )
                    results[i]["vlm_analysis"] = vlm_result
                    vlm_count += 1

                    if not quiet:
                        if vlm_result["success"]:
                            content_preview = vlm_result['content'][:200] + "..." \
                                if len(vlm_result['content']) > 200 else vlm_result['content']
                            print(f"    VLM: {content_preview}")
                        else:
                            print(f"    VLM错误: {vlm_result.get('error', '未知错误')}")
            elif dry_run and vlm_queue:
                print(f"\n[DRY-RUN] 跳过VLM分析，待分析数量: {len(vlm_queue)} 条")

            # 打印统计
            print("\n" + "=" * 60)
            print("统计摘要:")
            print("=" * 60)

            total = len(activities)
            immediate = sum(1 for r in results if r["decision"] == "immediate")
            batch = sum(1 for r in results if r["decision"] == "batch")
            skip = sum(1 for r in results if r["decision"] == "skip")
            filtered = sum(1 for r in results if r["decision"] == "filtered")

            print(f"总活动数: {total}")
            print(f"  - IMMEDIATE (立即分析): {immediate} ({immediate/total*100:.1f}%)")
            print(f"  - BATCH (批处理): {batch} ({batch/total*100:.1f}%)")
            print(f"  - SKIP (跳过): {skip} ({skip/total*100:.1f}%)")
            print(f"  - FILTERED (过滤): {filtered} ({filtered/total*100:.1f}%)")
            print(f"\n待VLM分析数量: {len(vlm_queue)}")
            print(f"已完成VLM分析: {vlm_count}")

            # 保存结果
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = OUTPUT_DIR / f"vlm_test_{timestamp}.json"

            save_data = {
                "analysis_time": datetime.now().isoformat(),
                "config": {
                    "hours": hours,
                    "immediate_threshold": immediate_threshold,
                    "batch_threshold": batch_threshold,
                    "max_vlm_calls": max_vlm_calls,
                    "include_batch": include_batch,
                },
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                },
                "summary": {
                    "total_activities": total,
                    "immediate_count": immediate,
                    "batch_count": batch,
                    "skip_count": skip,
                    "filtered_count": filtered,
                    "vlm_analysis_count": vlm_count,
                    "pending_vlm_count": len(vlm_queue),
                },
                "activities": results,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"\n结果已保存至: {output_file}")

            # 返回输出文件路径（供后续脚本使用）
            return str(output_file)

    except Exception as e:
        print(f"分析过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    result = asyncio.run(main())
    if isinstance(result, str):
        # 成功，返回0
        sys.exit(0)
    else:
        sys.exit(result)
