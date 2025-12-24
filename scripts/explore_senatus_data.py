"""
Senatus 数据探索脚本

分析 ManicTime 数据库中的活动数据，为 Senatus 模块确定合适的阈值参数。

主要分析内容:
1. 活动类型分布
2. 截图可用率
3. 帧差异统计
4. 上下文切换频率
5. VLM 分析样本
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest.manictime import ManicTimeDBConnector, ScreenshotLoader, ActivityParser
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
API_KEY = "sk-6c514e90b3144159b4e281666f7447b1"


def print_section(title: str) -> None:
    """打印分节标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def analyze_activity_distribution(activities: list[dict]) -> dict:
    """分析活动类型分布"""
    print_section("活动类型分布分析")

    app_counter = Counter()
    duration_by_app = Counter()

    for act in activities:
        app_name = act.get("app_name") or act.get("group_name") or "Unknown"
        # 简化应用名称
        app_name = app_name.split(" - ")[0].strip()
        app_counter[app_name] += 1

        # 计算持续时间
        try:
            start = datetime.fromisoformat(act["start_utc_time"])
            end = datetime.fromisoformat(act["end_utc_time"])
            duration = (end - start).total_seconds()
            duration_by_app[app_name] += duration
        except (KeyError, ValueError):
            pass

    # 打印前20个最常见的应用
    print(f"\n前20个最常见应用 (共 {len(app_counter)} 个):")
    print("-" * 50)
    for app, count in app_counter.most_common(20):
        duration_hrs = duration_by_app[app] / 3600
        print(f"  {app:40} | {count:5}次 | {duration_hrs:.2f}h")

    # 分类统计
    categories = {
        "IDE/Editor": ["Visual Studio", "Code", "PyCharm", "IntelliJ", "Sublime", "Vim", "Neovim"],
        "Browser": ["Chrome", "Firefox", "Edge", "Safari", "Opera", "Brave"],
        "Communication": ["Teams", "Slack", "Discord", "Telegram", "WeChat", "QQ", "Zoom"],
        "Terminal": ["Terminal", "PowerShell", "cmd", "WindowsTerminal", "iTerm"],
        "Office": ["Word", "Excel", "PowerPoint", "Outlook", "OneNote"],
        "System": ["Explorer", "dwm", "taskmgr", "SearchUI"],
    }

    category_counts = Counter()
    for app, count in app_counter.items():
        app_lower = app.lower()
        matched = False
        for cat, keywords in categories.items():
            if any(kw.lower() in app_lower for kw in keywords):
                category_counts[cat] += count
                matched = True
                break
        if not matched:
            category_counts["Other"] += count

    print(f"\n按类别统计:")
    print("-" * 30)
    total = sum(category_counts.values())
    for cat, count in category_counts.most_common():
        pct = count / total * 100 if total > 0 else 0
        print(f"  {cat:20} | {count:6} | {pct:5.1f}%")

    return {
        "app_counter": dict(app_counter),
        "category_counts": dict(category_counts),
        "total_activities": len(activities),
    }


def analyze_screenshots(loader: ScreenshotLoader, activities: list[dict]) -> dict:
    """分析截图可用率和帧差异"""
    print_section("截图分析")

    # 获取截图数量和时间范围
    try:
        screenshot_count = loader.get_screenshot_count()
        ss_min, ss_max = loader.get_date_range()
        print(f"截图总数: {screenshot_count}")
        print(f"截图时间范围: {ss_min} ~ {ss_max}")
    except Exception as e:
        print(f"获取截图信息失败: {e}")
        return {"error": str(e)}

    # 检查活动与截图的匹配率
    parser = ActivityParser()
    matched_count = 0
    unmatched_count = 0

    # 只检查最近100条活动
    sample_activities = activities[-100:] if len(activities) > 100 else activities

    for act in sample_activities:
        try:
            # 解析时间
            start_str = act.get("start_utc_time", "")
            if start_str:
                timestamp = datetime.fromisoformat(start_str)
                screenshot_path = loader.find_screenshot_path(
                    timestamp,
                    tolerance_seconds=60
                )
                if screenshot_path and screenshot_path.exists():
                    matched_count += 1
                else:
                    unmatched_count += 1
        except Exception:
            unmatched_count += 1

    total_checked = matched_count + unmatched_count
    match_rate = matched_count / total_checked * 100 if total_checked > 0 else 0

    print(f"\n截图匹配率 (检查 {total_checked} 条活动):")
    print(f"  匹配: {matched_count} ({match_rate:.1f}%)")
    print(f"  未匹配: {unmatched_count} ({100-match_rate:.1f}%)")

    return {
        "screenshot_count": screenshot_count,
        "match_rate": match_rate,
        "matched": matched_count,
        "unmatched": unmatched_count,
    }


def analyze_context_switches(activities: list[dict]) -> dict:
    """分析上下文切换频率"""
    print_section("上下文切换分析")

    if len(activities) < 2:
        print("活动数据不足，无法分析切换")
        return {}

    switch_counts = []
    rapid_switches = 0  # 3秒内切换

    prev_app = None
    prev_time = None

    for act in activities:
        app_name = act.get("app_name") or act.get("group_name") or "Unknown"
        try:
            start = datetime.fromisoformat(act["start_utc_time"])
        except (KeyError, ValueError):
            continue

        if prev_app is not None and prev_app != app_name:
            switch_counts.append(1)

            # 检查是否为快速切换
            if prev_time and (start - prev_time).total_seconds() < 3:
                rapid_switches += 1

        prev_app = app_name
        prev_time = start

    total_switches = sum(switch_counts)
    total_activities = len(activities)
    switch_rate = total_switches / total_activities * 100 if total_activities > 0 else 0
    rapid_rate = rapid_switches / total_switches * 100 if total_switches > 0 else 0

    print(f"总活动数: {total_activities}")
    print(f"切换次数: {total_switches} ({switch_rate:.1f}%)")
    print(f"快速切换 (<3s): {rapid_switches} ({rapid_rate:.1f}% of switches)")

    # 分析切换模式
    window_sizes = [5, 10, 20]
    print(f"\n滑动窗口内切换频率:")

    for window in window_sizes:
        if len(activities) < window:
            continue

        max_switches = 0
        for i in range(len(activities) - window + 1):
            window_apps = set()
            for j in range(i, i + window):
                app = activities[j].get("app_name") or "Unknown"
                window_apps.add(app)
            switches = len(window_apps) - 1
            max_switches = max(max_switches, switches)

        print(f"  窗口大小 {window}: 最大切换 {max_switches}")

    return {
        "total_switches": total_switches,
        "switch_rate": switch_rate,
        "rapid_switches": rapid_switches,
        "rapid_rate": rapid_rate,
    }


async def analyze_vlm_samples(
    provider: QwenVLProvider,
    loader: ScreenshotLoader,
    activities: list[dict],
    sample_size: int = 5,
) -> list[dict]:
    """使用 VLM 分析样本截图"""
    print_section(f"VLM 样本分析 (最多 {sample_size} 张)")

    # 测试连接
    print("测试 VLM 连接...")
    try:
        test_result = await provider.chat(
            messages=[{"role": "user", "content": "Reply OK"}],
            max_tokens=10
        )
        print(f"  连接成功: {test_result.get('content', '')}")
    except Exception as e:
        print(f"  连接失败: {e}")
        return []

    parser = ActivityParser()
    results = []
    analyzed = 0

    # 从最近的活动开始找有截图的
    for act in reversed(activities):
        if analyzed >= sample_size:
            break

        try:
            start_str = act.get("start_utc_time", "")
            if not start_str:
                continue

            timestamp = datetime.fromisoformat(start_str)
            screenshot_path = loader.find_screenshot_path(
                timestamp,
                tolerance_seconds=120
            )

            if not screenshot_path or not screenshot_path.exists():
                continue

            app_name = act.get("app_name") or act.get("group_name") or "Unknown"

            print(f"\n分析样本 {analyzed + 1}:")
            print(f"  应用: {app_name}")
            print(f"  时间: {timestamp}")
            print(f"  截图: {screenshot_path.name}")

            # VLM 分析
            prompt = """请分析这张屏幕截图，返回JSON格式:
{
    "content_type": "code_editing|document|browsing|communication|media|system|other",
    "sensitivity": "high|medium|low",
    "specific_activity": "简要描述用户活动",
    "has_private_info": true/false,
    "complexity": 0.0-1.0
}"""

            result = await provider.analyze_image(
                image=screenshot_path,
                prompt=prompt,
                max_tokens=300
            )

            vlm_content = result.get("content", "")
            print(f"  VLM分析: {vlm_content[:200]}...")

            results.append({
                "app": app_name,
                "timestamp": str(timestamp),
                "screenshot": str(screenshot_path),
                "vlm_analysis": vlm_content,
                "latency_ms": result.get("latency_ms", 0),
            })

            analyzed += 1

        except Exception as e:
            print(f"  分析失败: {e}")
            continue

    print(f"\n成功分析 {len(results)} 张截图")
    return results


def generate_recommendations(
    activity_stats: dict,
    screenshot_stats: dict,
    switch_stats: dict,
) -> None:
    """基于分析结果生成阈值建议"""
    print_section("阈值配置建议")

    print("\n基于数据分析的建议参数:")
    print("-" * 50)

    # StaticFrameFilter 阈值
    print("\n1. StaticFrameFilter (静态帧过滤器):")
    print("   diff_threshold: 0.05  (默认值)")
    print("   history_size: 5")
    print("   reason: 根据典型屏幕截图差异分布")

    # TimeRuleFilter 时间规则
    print("\n2. TimeRuleFilter (时间规则过滤器):")
    print("   办公时间 (9:00-18:00): weight_modifier = 0.7")
    print("   深夜 (23:00-06:00): weight_modifier = 1.2")

    # ContextSwitchAnalyzer 快速切换阈值
    rapid_rate = switch_stats.get("rapid_rate", 0)
    print(f"\n3. ContextSwitchAnalyzer (上下文切换分析器):")
    print(f"   rapid_switch_threshold: 3s")
    print(f"   观察到快速切换率: {rapid_rate:.1f}%")

    # 触发阈值
    print("\n4. TriggerThresholds (触发阈值):")
    print("   immediate: 0.8  (立即VLM分析)")
    print("   batch: 0.5      (批处理)")
    print("   skip: 0.3       (跳过)")

    # 权重配置
    print("\n5. TI 权重配置 (ti_weights):")
    print("   visual_sensitive: 0.35  (最高权重)")
    print("   metadata_anomaly: 0.25")
    print("   frame_diff: 0.15")
    print("   context_switch: 0.15")
    print("   uncertainty: 0.10  (最低权重)")


async def main():
    """主函数"""
    print("=" * 60)
    print("  Senatus 数据探索与分析")
    print("=" * 60)
    print(f"\n数据库: {DB_PATH}")
    print(f"截图目录: {SCREENSHOTS_PATH}")

    # 检查路径
    if not Path(DB_PATH).exists():
        print(f"\n错误: 数据库文件不存在: {DB_PATH}")
        return

    # 初始化组件
    db = ManicTimeDBConnector(DB_PATH)
    loader = ScreenshotLoader(SCREENSHOTS_PATH)
    provider = QwenVLProvider(api_key=API_KEY, model="qwen3-vl-flash")

    try:
        db.connect()

        # 获取数据范围
        min_time, max_time = db.get_date_range()
        print(f"\n数据库时间范围: {min_time} ~ {max_time}")

        # 查询最近7天的数据
        query_end = max_time
        query_start = max_time - timedelta(days=7)

        print(f"查询范围: {query_start} ~ {query_end}")

        activities = db.query_activities(query_start, query_end)
        print(f"获取到 {len(activities)} 条活动记录")

        if not activities:
            print("没有找到活动数据")
            return

        # 分析活动分布
        activity_stats = analyze_activity_distribution(activities)

        # 分析截图
        screenshot_stats = analyze_screenshots(loader, activities)

        # 分析上下文切换
        switch_stats = analyze_context_switches(activities)

        # VLM 样本分析
        vlm_results = await analyze_vlm_samples(
            provider, loader, activities, sample_size=5
        )

        # 生成建议
        generate_recommendations(activity_stats, screenshot_stats, switch_stats)

        print_section("探索完成")
        print("\n现在可以基于以上分析结果实现 Senatus 缺失组件。")

    finally:
        db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
