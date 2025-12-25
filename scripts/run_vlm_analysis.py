"""
VLM 分析脚本

读取 TI 计算结果 JSON 文件，对符合阈值条件的活动执行 VLM 分析。

用法:
    python run_vlm_analysis.py <json_file> [--threshold 阈值] [--max-vlm 数量]

示例:
    python run_vlm_analysis.py data/ti_results/ti_batch_xxx.json
    python run_vlm_analysis.py data/ti_results/ti_batch_xxx.json --threshold 0.45 --max-vlm 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.core import setup_logging, get_logger
from src.admina.providers.qwen_provider import QwenVLProvider

# 默认配置
DEFAULT_THRESHOLD = 0.45  # 默认分析阈值
DEFAULT_MAX_VLM_CALLS = 0
DEFAULT_CONCURRENCY = 5   # 默认并发数
DEFAULT_MODEL = "qwen-vl-max-latest"  # 默认VLM模型

# VLM分析提示词 (与 test_vlm_analysis.py 保持一致)
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
        description="VLM 分析脚本 - 对 TI 计算结果执行 VLM 分析"
    )
    parser.add_argument(
        "json_file",
        type=str,
        help="TI 计算结果 JSON 文件路径"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"TI 阈值，仅分析大于等于此值的活动 (默认: {DEFAULT_THRESHOLD})"
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
        help="包含 BATCH 类型活动进行分析"
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"并发数 (默认: {DEFAULT_CONCURRENCY})"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"VLM模型 (默认: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="减少输出信息"
    )
    return parser.parse_args()


def _sync_analyze(provider: QwenVLProvider, screenshot_path: Path) -> dict:
    """同步VLM分析 (在线程中执行)"""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            provider.analyze_image(
                image=screenshot_path,
                prompt=ANALYSIS_PROMPT,
                max_tokens=1024,
                temperature=0.3,
            )
        )
    finally:
        loop.close()


async def analyze_with_vlm(
    provider: QwenVLProvider,
    screenshot_path: Path,
    semaphore: asyncio.Semaphore,
    activity: dict,
    idx: int,
    total: int,
    quiet: bool,
) -> dict:
    """
    使用VLM分析截图 (带并发控制，真正并行)

    Args:
        provider: VLM提供商
        screenshot_path: 截图路径
        semaphore: 并发控制信号量
        activity: 活动信息
        idx: 当前索引
        total: 总数
        quiet: 静默模式

    Returns:
        分析结果字典
    """
    async with semaphore:
        if not quiet:
            print(f"[{idx + 1}/{total}] 开始 | "
                  f"{activity['date']} {activity['time_str']} | "
                  f"TI={activity['ti_score']:.3f} | {activity['application']}")

        try:
            # 使用线程池执行同步调用，实现真正并发
            result = await asyncio.to_thread(
                _sync_analyze, provider, screenshot_path
            )
            vlm_result = {
                "success": True,
                "content": result.get("content", ""),
                "usage": result.get("usage", {}),
                "latency_ms": result.get("latency_ms", 0),
            }
            if not quiet:
                print(f"[{idx + 1}/{total}] 完成 | 耗时: {vlm_result['latency_ms']:.0f}ms")
        except Exception as e:
            logger.error(f"VLM分析失败: {e}")
            vlm_result = {
                "success": False,
                "error": str(e),
            }
            if not quiet:
                print(f"[{idx + 1}/{total}] 失败 | {e}")

        return {
            **activity,
            "vlm_analysis": vlm_result,
        }


async def main():
    """主函数"""
    args = parse_args()
    setup_logging()

    json_file = Path(args.json_file)
    threshold = args.threshold
    max_vlm_calls = args.max_vlm
    include_batch = args.include_batch
    concurrency = args.concurrency
    model = args.model
    quiet = args.quiet

    print("=" * 60)
    print("       VLM 分析 - 基于 TI 计算结果")
    print("=" * 60)

    # 检查输入文件
    if not json_file.exists():
        print(f"错误: 文件不存在: {json_file}")
        return 1

    # 加载 JSON 数据
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"错误: 无法读取 JSON 文件: {e}")
        return 1

    print(f"输入文件: {json_file}")
    print(f"分析时间: {data.get('analysis_time', 'N/A')}")
    print(f"时间范围: {data.get('time_range', {}).get('start', 'N/A')} ~ "
          f"{data.get('time_range', {}).get('end', 'N/A')}")
    print(f"\n配置: TI阈值>={threshold}, 最大VLM调用={'不限制' if max_vlm_calls == 0 else max_vlm_calls}")
    print(f"      包含BATCH类型: {'是' if include_batch else '否'}, 并发数: {concurrency}")
    print(f"      模型: {model}")

    activities = data.get("activities", [])
    if not activities:
        print("没有找到活动记录")
        return 0

    print(f"总活动数: {len(activities)}")

    # 筛选需要 VLM 分析的活动
    vlm_queue = []
    for activity in activities:
        ti_score = activity.get("ti_score", 0)
        decision = activity.get("decision", "")
        screenshot_path = activity.get("screenshot_path")

        if not screenshot_path:
            continue

        needs_vlm = False
        if decision == "immediate" and ti_score >= threshold:
            needs_vlm = True
        elif include_batch and decision == "batch" and ti_score >= threshold:
            needs_vlm = True

        if needs_vlm:
            vlm_queue.append(activity)

    print(f"符合条件的活动: {len(vlm_queue)}")

    if not vlm_queue:
        print("没有符合条件的活动需要 VLM 分析")
        return 0

    # 初始化 VLM 提供商
    print("\n尝试连接 VLM 服务...")
    try:
        vlm_provider = QwenVLProvider(model=model)
        health = await vlm_provider.health_check()
        if not health.is_healthy:
            print(f"错误: VLM 服务不可用 - {health.message}")
            return 1
        print(f"  Qwen VL ({model}): 正常 (延迟: {health.latency_ms:.0f}ms)")
    except Exception as e:
        print(f"错误: 无法连接 VLM 服务 - {e}")
        return 1

    # 限制 VLM 调用次数
    if max_vlm_calls > 0 and len(vlm_queue) > max_vlm_calls:
        print(f"\n限制 VLM 调用次数为 {max_vlm_calls}")
        vlm_queue = vlm_queue[:max_vlm_calls]

    # 执行 VLM 分析 (并行)
    print(f"\n开始 VLM 分析 ({len(vlm_queue)} 条, 并发={concurrency})...")

    semaphore = asyncio.Semaphore(concurrency)
    total = len(vlm_queue)

    tasks = [
        analyze_with_vlm(
            provider=vlm_provider,
            screenshot_path=Path(activity["screenshot_path"]),
            semaphore=semaphore,
            activity=activity,
            idx=idx,
            total=total,
            quiet=quiet,
        )
        for idx, activity in enumerate(vlm_queue)
    ]

    vlm_results = await asyncio.gather(*tasks)
    success_count = sum(1 for r in vlm_results if r.get("vlm_analysis", {}).get("success"))

    # 统计
    print("\n" + "=" * 60)
    print("VLM 分析完成:")
    print("=" * 60)
    print(f"总分析数: {total}")
    print(f"成功: {success_count}")
    print(f"失败: {total - success_count}")

    # 保存结果
    output_dir = PROJECT_ROOT / "data" / "vlm_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"vlm_result_{timestamp}.json"

    save_data = {
        "analysis_time": datetime.now().isoformat(),
        "source_file": str(json_file),
        "config": {
            "threshold": threshold,
            "max_vlm_calls": max_vlm_calls,
            "include_batch": include_batch,
            "concurrency": concurrency,
            "model": model,
        },
        "summary": {
            "total_analyzed": total,
            "success_count": success_count,
            "failed_count": total - success_count,
        },
        "results": vlm_results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n结果已保存至: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
