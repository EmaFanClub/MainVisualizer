"""
TI 批量计算脚本

批量计算活动的 Trigger Index (TI)，并保存结果到 JSON 文件。
此脚本专注于 TI 计算和统计，不执行 VLM 分析。

用法:
    python calculate_ti_batch.py [小时数] [--threshold 阈值]

示例:
    python calculate_ti_batch.py 168           # 分析7天(168小时)
    python calculate_ti_batch.py 24 --threshold 0.45
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.core import setup_logging, get_logger
from src.ingest.manictime import ManicTimeDBConnector, ActivityParser, ScreenshotLoader
from src.senatus import SenatusEngine
from src.senatus.trigger_manager import TriggerThresholds

# 路径配置 (与 test_vlm_analysis.py 保持一致)
DB_PATH = Path(r"D:\code_field\manicData\db\ManicTimeReports.db")
SCREENSHOTS_PATH = Path(r"Y:\临时文件\ManicTimeScreenShots")
OUTPUT_DIR = PROJECT_ROOT / "data" / "ti_results"

# 默认配置
DEFAULT_LOOKBACK_HOURS = 24
DEFAULT_IMMEDIATE_THRESHOLD = 0.55
DEFAULT_BATCH_THRESHOLD = 0.45

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="TI 批量计算脚本 - 计算活动的 Trigger Index"
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
        "--output", "-o",
        type=str,
        default=None,
        help="输出文件路径 (默认: 自动生成)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="减少输出信息"
    )
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    setup_logging()

    hours = args.hours
    immediate_threshold = args.threshold
    batch_threshold = args.batch_threshold
    quiet = args.quiet

    days = hours / 24

    print("=" * 60)
    if days >= 1:
        print(f"       TI 批量计算 - 最近 {days:.1f} 天 ({hours}小时)")
    else:
        print(f"       TI 批量计算 - 最近 {hours} 小时")
    print("=" * 60)
    print(f"配置: 阈值={immediate_threshold}, 批处理阈值={batch_threshold}")

    # 检查数据库
    if not DB_PATH.exists():
        print(f"错误: 数据库文件不存在: {DB_PATH}")
        return 1

    # 初始化组件
    parser = ActivityParser(local_timezone_hours=8)
    thresholds = TriggerThresholds(
        immediate_threshold=immediate_threshold,
        batch_threshold=batch_threshold,
        skip_threshold=0.30,
    )
    engine = SenatusEngine(thresholds=thresholds)

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

            # 数据库查询
            t0 = time.time()
            raw_activities = db.query_activities(start_time, end_time)
            t1 = time.time()
            print(f"[计时] 数据库查询: {t1-t0:.2f}s")

            applications = db.query_applications_model()
            app_map = {app.common_id: app for app in applications}

            # 解析活动
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
                print("开始TI计算...")
                print("-" * 60)

            results = []
            ti_start = time.time()
            screenshot_time = 0.0
            ti_calc_time = 0.0

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

                ti_score = decision.ti_score if decision.ti_score is not None else 0.0
                result = {
                    "index": i + 1,
                    "timestamp": activity.timestamp.isoformat(),
                    "time_str": activity.timestamp.strftime("%H:%M:%S"),
                    "date": activity.timestamp.strftime("%Y-%m-%d"),
                    "application": activity.application,
                    "window_title": activity.window_title[:80] if activity.window_title else "",
                    "duration": activity.duration_seconds,
                    "ti_score": round(ti_score, 4),
                    "decision": decision.decision_type.value,
                    "has_screenshot": screenshot_path is not None,
                    "screenshot_path": str(screenshot_path) if screenshot_path else None,
                }
                results.append(result)

                # 进度显示
                if not quiet and ((i + 1) % 50 == 0 or i == len(activities) - 1):
                    elapsed = time.time() - ti_start
                    speed = (i + 1) / elapsed if elapsed > 0 else 0
                    remaining = (len(activities) - i - 1) / speed if speed > 0 else 0
                    print(f"\r  进度: {i + 1}/{len(activities)} "
                          f"({(i + 1) / len(activities) * 100:.1f}%) "
                          f"[{elapsed:.1f}s, {speed:.1f}条/秒, 剩余~{remaining:.0f}s]    ",
                          end="", flush=True)

            if not quiet:
                print()

            ti_end = time.time()
            print(f"\n[计时] TI计算总耗时: {ti_end-ti_start:.2f}s")
            print(f"  - 截图加载: {screenshot_time:.2f}s")
            print(f"  - TI计算: {ti_calc_time:.2f}s")

            # 统计
            total = len(activities)
            immediate = sum(1 for r in results if r["decision"] == "immediate")
            batch = sum(1 for r in results if r["decision"] == "batch")
            skip = sum(1 for r in results if r["decision"] == "skip")
            filtered = sum(1 for r in results if r["decision"] == "filtered")
            has_screenshot = sum(1 for r in results if r["has_screenshot"])

            # 打印统计
            print("\n" + "=" * 60)
            print("统计摘要:")
            print("=" * 60)
            print(f"总活动数: {total}")
            print(f"  - IMMEDIATE (立即分析): {immediate} ({immediate/total*100:.1f}%)")
            print(f"  - BATCH (批处理): {batch} ({batch/total*100:.1f}%)")
            print(f"  - SKIP (跳过): {skip} ({skip/total*100:.1f}%)")
            print(f"  - FILTERED (过滤): {filtered} ({filtered/total*100:.1f}%)")
            print(f"\n有截图的活动: {has_screenshot} ({has_screenshot/total*100:.1f}%)")

            # 保存结果
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if args.output:
                output_file = Path(args.output)
            else:
                output_file = OUTPUT_DIR / f"ti_batch_{timestamp}.json"

            save_data = {
                "analysis_time": datetime.now().isoformat(),
                "config": {
                    "hours": hours,
                    "immediate_threshold": immediate_threshold,
                    "batch_threshold": batch_threshold,
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
                    "has_screenshot_count": has_screenshot,
                },
                "activities": results,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"\n结果已保存至: {output_file}")
            print("\n可使用以下命令进行 VLM 分析:")
            print(f"  python scripts/run_vlm_analysis.py \"{output_file}\"")

            return 0

    except Exception as e:
        print(f"分析过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
