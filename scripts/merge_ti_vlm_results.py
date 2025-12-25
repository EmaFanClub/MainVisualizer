"""
合并 TI 计算结果和 VLM 分析结果

将 ti_batch 和 vlm_result 文件整合为统一的结果文件。

用法:
    python merge_ti_vlm_results.py                   # 自动查找最新的 TI 和 VLM 文件
    python merge_ti_vlm_results.py <ti_batch_file>   # 指定 TI 文件，自动查找 VLM
    python merge_ti_vlm_results.py <ti_batch> <vlm>  # 手动指定两个文件

输出:
    data/merged_results/merged.json          # 完整合并结果
    data/merged_results/activity_summary.json # 按时间槽分组的活动摘要
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "data" / "merged_results"
TI_RESULTS_DIR = PROJECT_ROOT / "data" / "ti_results"
VLM_ANALYSIS_DIR = PROJECT_ROOT / "data" / "vlm_analysis"


def find_latest_ti_batch() -> Path | None:
    """查找最新的 TI 批量结果文件"""
    if not TI_RESULTS_DIR.exists():
        return None
    files = list(TI_RESULTS_DIR.glob("ti_batch_*.json"))
    if not files:
        return None
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0]


def find_latest_vlm_result() -> Path | None:
    """查找最新的 VLM 分析结果文件"""
    if not VLM_ANALYSIS_DIR.exists():
        return None
    files = list(VLM_ANALYSIS_DIR.glob("vlm_result_*.json"))
    if not files:
        return None
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0]


def get_time_slot(timestamp_str: str) -> str:
    """
    获取1小时时间段的起始时间
    支持 ISO 格式 (2025-12-18T16:48:21+08:00) 和简单格式 (16:48:21)

    Args:
        timestamp_str: 时间字符串

    Returns:
        时间槽字符串 (HH:00:00)
    """
    # 提取时间部分
    if 'T' in timestamp_str:
        # ISO 格式: 2025-12-18T16:48:21+08:00
        time_part = timestamp_str.split('T')[1]
        if '+' in time_part:
            time_part = time_part.split('+')[0]
        elif '-' in time_part and time_part.count('-') == 1:
            time_part = time_part.rsplit('-', 1)[0]
    else:
        time_part = timestamp_str

    parts = time_part.split(':')
    hour = int(parts[0])

    # 1小时时间段
    return f"{hour:02d}:00:00"


def get_date_from_timestamp(timestamp_str: str) -> str:
    """从时间戳中提取日期"""
    if 'T' in timestamp_str:
        return timestamp_str.split('T')[0]
    return ""


def generate_activity_summary(merged_data: dict) -> dict:
    """
    从合并数据生成 activity_summary 格式

    Args:
        merged_data: 合并后的数据

    Returns:
        activity_summary 格式的字典
    """
    # 按 (日期, 时间槽) 分组
    time_slots: dict[tuple[str, str], list[dict]] = {}

    for activity in merged_data.get("activities", []):
        timestamp = activity.get("timestamp", "")
        if not timestamp:
            continue

        date = get_date_from_timestamp(timestamp)
        time_slot = get_time_slot(timestamp)
        key = (date, time_slot)

        if key not in time_slots:
            time_slots[key] = []

        # 提取所需字段: duration, window_title, content(可选)
        entry = {
            "duration": activity.get("duration"),
            "window_title": activity.get("window_title", ""),
        }

        # 如果有 VLM 分析，添加 content
        vlm_analysis = activity.get("vlm_analysis")
        if vlm_analysis and vlm_analysis.get("content"):
            entry["content"] = vlm_analysis["content"]

        time_slots[key].append(entry)

    # 按 (日期, 时间槽) 排序
    sorted_keys = sorted(time_slots.keys())

    # 构建输出
    output_slots = []
    for date, slot in sorted_keys:
        # timestamp 包含日期和时间，格式: 2025-12-18 16:30:00
        full_timestamp = f"{date} {slot}" if date else slot
        slot_data = {
            "timestamp": full_timestamp,
            "activities": time_slots[(date, slot)]
        }
        output_slots.append(slot_data)

    summary_data = {
        "source_files": merged_data.get("source_files", {}),
        "time_range": merged_data.get("time_range", {}),
        "ti_config": merged_data.get("ti_config", {}),
        "extraction_time": datetime.now().isoformat(),
        "summary": {
            "total_time_slots": len(sorted_keys),
            "total_activities": sum(len(v) for v in time_slots.values()),
            "activities_with_vlm": sum(
                1 for slot in time_slots.values()
                for entry in slot
                if "content" in entry
            ),
        },
        "time_slots": output_slots,
    }

    return summary_data


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="合并 TI 计算结果和 VLM 分析结果"
    )
    parser.add_argument(
        "ti_batch_file",
        type=str,
        nargs="?",
        default=None,
        help="TI 批量计算结果 JSON 文件 (可选，自动查找最新)"
    )
    parser.add_argument(
        "vlm_result_file",
        type=str,
        nargs="?",
        default=None,
        help="VLM 分析结果 JSON 文件 (可选，自动查找)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="输出文件路径 (默认: 自动生成)"
    )
    return parser.parse_args()


def find_vlm_results(ti_batch_path: Path) -> list[Path]:
    """查找引用了该 TI 批量文件的 VLM 结果文件"""
    vlm_dir = PROJECT_ROOT / "data" / "vlm_analysis"
    if not vlm_dir.exists():
        return []

    matching = []
    ti_batch_str = str(ti_batch_path)

    for vlm_file in vlm_dir.glob("vlm_result_*.json"):
        try:
            with open(vlm_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            source = data.get("source_file", "")
            # 检查是否引用了该 TI 批量文件
            if ti_batch_path.name in source or ti_batch_str in source:
                matching.append(vlm_file)
        except Exception:
            continue

    return sorted(matching, key=lambda p: p.stat().st_mtime, reverse=True)


def merge_results(ti_batch_path: Path, vlm_result_paths: list[Path]) -> dict:
    """
    合并 TI 和 VLM 结果

    Args:
        ti_batch_path: TI 批量结果文件
        vlm_result_paths: VLM 结果文件列表 (按优先级排序)

    Returns:
        合并后的结果字典
    """
    # 加载 TI 批量结果
    with open(ti_batch_path, "r", encoding="utf-8") as f:
        ti_data = json.load(f)

    # 构建 VLM 结果索引 (按 index 和 timestamp)
    vlm_by_index = {}
    vlm_by_timestamp = {}
    vlm_configs = []

    for vlm_path in vlm_result_paths:
        with open(vlm_path, "r", encoding="utf-8") as f:
            vlm_data = json.load(f)

        vlm_configs.append({
            "file": str(vlm_path),
            "config": vlm_data.get("config", {}),
            "summary": vlm_data.get("summary", {}),
        })

        for result in vlm_data.get("results", []):
            idx = result.get("index")
            ts = result.get("timestamp")
            vlm_analysis = result.get("vlm_analysis")

            if vlm_analysis and vlm_analysis.get("success"):
                if idx and idx not in vlm_by_index:
                    vlm_by_index[idx] = vlm_analysis
                if ts and ts not in vlm_by_timestamp:
                    vlm_by_timestamp[ts] = vlm_analysis

    # 合并到 TI 结果
    activities = ti_data.get("activities", [])
    merged_count = 0

    for activity in activities:
        idx = activity.get("index")
        ts = activity.get("timestamp")

        vlm_analysis = None
        if idx in vlm_by_index:
            vlm_analysis = vlm_by_index[idx]
        elif ts in vlm_by_timestamp:
            vlm_analysis = vlm_by_timestamp[ts]

        activity["vlm_analysis"] = vlm_analysis
        if vlm_analysis:
            merged_count += 1

    # 构建合并结果
    merged_data = {
        "merge_time": datetime.now().isoformat(),
        "source_files": {
            "ti_batch": str(ti_batch_path),
            "vlm_results": [str(p) for p in vlm_result_paths],
        },
        "ti_config": ti_data.get("config", {}),
        "vlm_configs": vlm_configs,
        "time_range": ti_data.get("time_range", {}),
        "summary": {
            **ti_data.get("summary", {}),
            "vlm_analyzed_count": merged_count,
        },
        "activities": activities,
    }

    return merged_data


def main():
    """主函数"""
    args = parse_args()

    # 确定 TI 批量文件
    if args.ti_batch_file:
        ti_batch_path = Path(args.ti_batch_file)
    else:
        print("未指定 TI 批量文件，正在查找最新文件...")
        ti_batch_path = find_latest_ti_batch()
        if ti_batch_path is None:
            print(f"错误: 在 {TI_RESULTS_DIR} 中未找到 TI 批量文件")
            return 1
        print(f"找到最新 TI 批量文件: {ti_batch_path.name}")

    if not ti_batch_path.exists():
        print(f"错误: TI 批量文件不存在: {ti_batch_path}")
        return 1

    print("=" * 60)
    print("       合并 TI 和 VLM 结果")
    print("=" * 60)
    print(f"TI 批量文件: {ti_batch_path}")

    # 确定 VLM 结果文件
    if args.vlm_result_file:
        vlm_paths = [Path(args.vlm_result_file)]
        if not vlm_paths[0].exists():
            print(f"错误: VLM 结果文件不存在: {vlm_paths[0]}")
            return 1
    else:
        # 先尝试查找引用了该 TI 文件的 VLM 结果
        vlm_paths = find_vlm_results(ti_batch_path)
        if not vlm_paths:
            # 如果没找到，尝试使用最新的 VLM 结果
            latest_vlm = find_latest_vlm_result()
            if latest_vlm:
                vlm_paths = [latest_vlm]
                print(f"使用最新 VLM 结果文件: {latest_vlm.name}")
            else:
                print("警告: 未找到 VLM 结果文件，将只包含 TI 结果")
        else:
            print(f"找到 {len(vlm_paths)} 个对应的 VLM 结果文件:")
            for p in vlm_paths:
                print(f"  - {p.name}")

    # 合并结果
    merged_data = merge_results(ti_batch_path, vlm_paths)

    # 保存结果
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.output:
        output_path = Path(args.output)
    else:
        # 使用固定文件名，新生成的文件会覆盖旧文件
        output_path = OUTPUT_DIR / "merged.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2, default=str)

    # 生成 activity_summary 格式文件
    summary_data = generate_activity_summary(merged_data)
    summary_path = OUTPUT_DIR / "activity_summary.json"

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2, default=str)

    # 打印统计
    summary = merged_data["summary"]
    print("\n" + "-" * 60)
    print("合并统计:")
    print("-" * 60)
    print(f"总活动数: {summary.get('total_activities', 0)}")
    print(f"IMMEDIATE: {summary.get('immediate_count', 0)}")
    print(f"BATCH: {summary.get('batch_count', 0)}")
    print(f"SKIP: {summary.get('skip_count', 0)}")
    print(f"FILTERED: {summary.get('filtered_count', 0)}")
    print(f"有截图: {summary.get('has_screenshot_count', 0)}")
    print(f"已VLM分析: {summary.get('vlm_analyzed_count', 0)}")

    print(f"\n输出文件:")
    print(f"  - 完整合并: {output_path}")
    print(f"  - 活动摘要: {summary_path}")
    print(f"\n活动摘要统计: {summary_data['summary']['total_time_slots']}个时间槽, "
          f"{summary_data['summary']['activities_with_vlm']}条含VLM分析")

    return 0


if __name__ == "__main__":
    sys.exit(main())
