"""
滑窗分析测试脚本

使用DeepSeek模型对活动摘要进行滑窗处理分析。
支持并发请求以提升处理速度，并显示实时进度。
自动查找 activity_summary.json 文件。

用法:
    python test_sliding_window.py [输入文件] [选项]

示例:
    python test_sliding_window.py                      # 自动查找 activity_summary.json
    python test_sliding_window.py summary.json         # 指定输入文件
    python test_sliding_window.py -c 15 -w 4 -s 2      # 15并发, 4槽窗口, 2槽步长
    python test_sliding_window.py -m 5                 # 只处理前5个窗口(测试)

输出:
    data/sliding_window/sliding_window_result.json    # 分析结果(固定名称，覆盖旧文件)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# DeepSeek配置
DEEPSEEK_API_KEY = "sk-75f331e7cc414f59a1868702e532e4c0"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
VLM_ANALYSIS_DIR = PROJECT_ROOT / "data" / "vlm_analysis"
MERGED_RESULTS_DIR = PROJECT_ROOT / "data" / "merged_results"
OUTPUT_DIR = PROJECT_ROOT / "data" / "sliding_window"

# 默认滑窗参数
# 每个时间槽30分钟
# window_size=3 表示1.5小时窗口
# step_size=2 表示1小时步长，0.5小时与前窗口重叠
DEFAULT_WINDOW_SIZE = 4  # 1.5小时窗口
DEFAULT_STEP_SIZE = 3    # 1小时步长

# 并发控制参数
DEFAULT_MAX_CONCURRENT = 150  # 最大并发请求数


def find_activity_summary() -> Path | None:
    """
    查找活动摘要文件

    优先级:
    1. merged_results/activity_summary.json (固定名称)
    2. vlm_analysis/activity_summary.json (固定名称)
    3. 任意目录中最新的 activity_summary_*.json (带时间戳)

    Returns:
        文件路径，如果没有找到则返回None
    """
    # 1. 优先查找固定名称文件
    fixed_paths = [
        MERGED_RESULTS_DIR / "activity_summary.json",
        VLM_ANALYSIS_DIR / "activity_summary.json",
    ]
    for path in fixed_paths:
        if path.exists():
            return path

    # 2. 查找带时间戳的文件
    all_files = []
    for directory in [MERGED_RESULTS_DIR, VLM_ANALYSIS_DIR]:
        if directory.exists():
            all_files.extend(directory.glob("activity_summary_*.json"))

    if not all_files:
        return None

    # 按修改时间排序，取最新的
    all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return all_files[0]


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="滑窗分析脚本 - 使用DeepSeek分析活动摘要"
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default=None,
        help="输入的活动摘要文件路径 (默认: 自动使用最新文件)"
    )
    parser.add_argument(
        "--window", "-w",
        type=int,
        default=DEFAULT_WINDOW_SIZE,
        help=f"窗口大小(时间槽数量) (默认: {DEFAULT_WINDOW_SIZE})"
    )
    parser.add_argument(
        "--step", "-s",
        type=int,
        default=DEFAULT_STEP_SIZE,
        help=f"滑动步长 (默认: {DEFAULT_STEP_SIZE})"
    )
    parser.add_argument(
        "--concurrent", "-c",
        type=int,
        default=DEFAULT_MAX_CONCURRENT,
        help=f"最大并发请求数 (默认: {DEFAULT_MAX_CONCURRENT})"
    )
    parser.add_argument(
        "--max-windows", "-m",
        type=int,
        default=None,
        help="最大处理窗口数，用于测试 (默认: 不限制)"
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


class SlidingWindowAnalyzer:
    """
    滑窗分析器

    对大型活动数据进行分窗处理，并发调用LLM进行分析。
    """

    def __init__(
        self,
        api_key: str = DEEPSEEK_API_KEY,
        base_url: str = DEEPSEEK_BASE_URL,
        model: str = DEEPSEEK_MODEL,
        window_size: int = DEFAULT_WINDOW_SIZE,
        step_size: int = DEFAULT_STEP_SIZE,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT
    ) -> None:
        """
        初始化滑窗分析器

        Args:
            api_key: DeepSeek API密钥
            base_url: API基础URL
            model: 模型名称
            window_size: 窗口大小（时间槽数量）
            step_size: 滑动步长
            max_concurrent: 最大并发请求数
        """
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._window_size = window_size
        self._step_size = step_size
        self._max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None
        # 进度跟踪
        self._total_windows = 0
        self._completed_windows = 0
        self._lock = asyncio.Lock() if asyncio else None

    def load_data(self, file_path: str | Path) -> dict:
        """
        加载JSON数据文件

        Args:
            file_path: JSON文件路径

        Returns:
            解析后的数据字典
        """
        file_path = Path(file_path)
        logger.info(f"加载数据文件: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        total_slots = len(data.get("time_slots", []))
        total_activities = data.get("summary", {}).get("total_activities", 0)
        logger.info(f"数据概览: {total_slots}个时间槽, {total_activities}个活动")

        return data

    def create_windows(self, time_slots: list[dict]) -> list[tuple[int, int, list[dict]]]:
        """
        创建滑动窗口

        Args:
            time_slots: 时间槽列表

        Returns:
            窗口列表，每个元素为(起始索引, 结束索引, 时间槽数据)
        """
        windows = []
        total = len(time_slots)

        start = 0
        while start < total:
            end = min(start + self._window_size, total)
            window_data = time_slots[start:end]
            windows.append((start, end, window_data))

            # 如果已到达末尾，退出
            if end >= total:
                break

            start += self._step_size

        logger.info(
            f"创建了{len(windows)}个滑动窗口 "
            f"(窗口大小={self._window_size}, 步长={self._step_size}, "
            f"最大并发={self._max_concurrent})"
        )
        return windows

    def format_window_context(self, window_data: list[dict], window_idx: int) -> str:
        """
        格式化窗口数据为LLM输入上下文

        Args:
            window_data: 窗口内的时间槽数据
            window_idx: 窗口索引

        Returns:
            格式化后的文本
        """
        lines = [f"=== 窗口 {window_idx + 1} ===\n"]

        for slot in window_data:
            timestamp = slot.get("timestamp", "未知时间")
            activities = slot.get("activities", [])

            lines.append(f"\n时间段: {timestamp}")
            lines.append(f"活动数量: {len(activities)}")

            # 统计有VLM分析的活动
            vlm_activities = [a for a in activities if a.get("content")]
            if vlm_activities:
                lines.append(f"VLM分析条目: {len(vlm_activities)}")
                for act in vlm_activities:
                    title = act.get("window_title", "未知窗口")
                    duration = act.get("duration", 0)
                    content_preview = act.get("content", "")[:200] + "..."
                    lines.append(f"  - [{title}] 持续{duration}秒")
                    lines.append(f"    内容摘要: {content_preview}")
            else:
                # 列出主要活动
                top_activities = sorted(
                    activities, key=lambda x: x.get("duration", 0), reverse=True
                )[:3]
                for act in top_activities:
                    title = act.get("window_title", "未知窗口")
                    duration = act.get("duration", 0)
                    lines.append(f"  - [{title}] 持续{duration}秒")

        return "\n".join(lines)

    def _build_system_prompt(self) -> str:
        """
        构建系统提示词

        使用CO-STAR框架设计详细的分析提示词。
        参考: Anthropic Context Engineering, Palantir Prompt Best Practices

        Returns:
            系统提示词
        """
        return """# 角色定义
你是一位专业的数字健康与生产力分析师，专注于通过屏幕活动数据洞察用户行为模式。
你具备心理学、人机交互和时间管理领域的专业知识。

# 任务目标
分析用户在特定时间窗口内的屏幕活动数据，提供深度洞察和可操作的建议。

# 分析框架
请按照以下六个维度进行详细分析：

## 1. 活动类型分类
将观察到的活动归类为以下类别，并计算各类别的时间占比：
- 深度工作：编程、文档撰写、设计等需要持续专注的任务
- 浅层工作：邮件处理、即时通讯、会议等碎片化任务
- 学习探索：阅读文章、观看教程、研究资料等
- 娱乐休闲：视频、游戏、社交媒体浏览等
- 系统操作：文件管理、设置调整、软件安装等

## 2. 注意力流分析
- 识别注意力的主要流向（哪些应用/内容获得最多关注）
- 检测注意力碎片化程度（切换频率、平均停留时间）
- 评估是否存在"注意力陷阱"（如无意识的社交媒体刷新）

## 3. 工作流模式识别
- 识别是否存在番茄工作法等时间管理模式
- 检测深度工作时段的长度和质量
- 分析任务切换的触发因素（主动切换 vs 被动中断）

## 4. 内容消费洞察
基于VLM分析的屏幕内容，提取：
- 关注的主题领域和知识点
- 信息获取的来源和质量
- 潜在的学习或工作目标推断

## 5. 数字健康评估
- 评估该时段的屏幕使用是否健康
- 识别可能的过度使用或成瘾迹象
- 分析是否有适当的休息间隔

## 6. 改进建议
基于以上分析，提供2-3条具体可行的建议，帮助用户：
- 提升专注度和生产力
- 优化时间分配
- 改善数字健康

# 输出要求
- 使用中文回答
- 每个维度提供详细分析（3-5句话）
- 用具体数据和观察支撑结论
- 建议应具体、可操作、针对性强
- 在分析结尾给出该时段的整体评价标签（如：高效深度工作期/碎片化浅层工作期/休闲娱乐期/混合过渡期）"""

    def _build_user_prompt(self, context: str, window_idx: int, time_range: str) -> str:
        """
        构建用户提示词

        Args:
            context: 窗口上下文
            window_idx: 窗口索引
            time_range: 时间范围描述

        Returns:
            用户提示词
        """
        return f"""请分析以下用户屏幕活动数据（时间窗口 {window_idx + 1}，时段：{time_range}）：

---
{context}
---

请按照系统提示中的六个分析维度，逐一给出详细分析。
注意：
1. 如果某些活动有VLM分析内容，请重点解读这些内容的含义
2. 关注活动之间的关联性和上下文
3. 结合时间戳判断这是一天中的什么时段（深夜/早晨/上午/下午/晚间）"""

    async def analyze_window(
        self,
        context: str,
        window_idx: int,
        time_range: str = ""
    ) -> Optional[str]:
        """
        使用LLM分析单个窗口（异步）

        Args:
            context: 窗口上下文文本
            window_idx: 窗口索引
            time_range: 时间范围描述

        Returns:
            LLM分析结果
        """
        # 使用信号量控制并发
        async with self._semaphore:
            logger.info(f"开始分析窗口 {window_idx + 1}...")
            start_time = time.time()

            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(context, window_idx, time_range)

            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2500  # 增加token限制以适应详细分析
                )
                result = response.choices[0].message.content
                elapsed = time.time() - start_time
                logger.info(f"窗口 {window_idx + 1} 分析完成 (耗时: {elapsed:.2f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"窗口 {window_idx + 1} 分析失败 (耗时: {elapsed:.2f}s): {e}")
                return None

    def _print_progress(self) -> None:
        """打印进度条"""
        if self._total_windows == 0:
            return
        pct = self._completed_windows / self._total_windows * 100
        bar_len = 30
        filled = int(bar_len * self._completed_windows / self._total_windows)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r进度: [{bar}] {self._completed_windows}/{self._total_windows} ({pct:.1f}%)", end="", flush=True)

    async def _analyze_single_window(
        self,
        idx: int,
        start: int,
        end: int,
        window_data: list[dict]
    ) -> dict:
        """
        分析单个窗口并返回结果字典

        Args:
            idx: 窗口索引
            start: 起始槽索引
            end: 结束槽索引
            window_data: 窗口数据

        Returns:
            包含分析结果的字典
        """
        # 获取时间范围描述
        start_time = window_data[0].get("timestamp", "?") if window_data else "?"
        end_time = window_data[-1].get("timestamp", "?") if window_data else "?"
        time_range_str = f"{start_time} - {end_time}"

        context = self.format_window_context(window_data, idx)
        analysis = await self.analyze_window(context, idx, time_range_str)

        # 更新进度
        async with self._lock:
            self._completed_windows += 1
            self._print_progress()

        return {
            "window_index": idx,
            "time_range": {
                "start_slot": start,
                "end_slot": end,
                "start_time": start_time,
                "end_time": end_time
            },
            "slot_count": len(window_data),
            "analysis": analysis
        }

    async def run_analysis_async(
        self,
        file_path: str | Path,
        max_windows: Optional[int] = None
    ) -> list[dict]:
        """
        执行滑窗分析（异步并发版本）

        Args:
            file_path: 数据文件路径
            max_windows: 最大处理窗口数（用于测试限制）

        Returns:
            分析结果列表
        """
        # 初始化信号量和锁
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        self._lock = asyncio.Lock()

        # 加载数据
        data = self.load_data(file_path)
        time_slots = data.get("time_slots", [])

        if not time_slots:
            logger.warning("没有时间槽数据可分析")
            return []

        # 创建窗口
        windows = self.create_windows(time_slots)

        # 限制窗口数量（测试用）
        if max_windows:
            windows = windows[:max_windows]
            logger.info(f"测试模式: 仅处理前{max_windows}个窗口")

        # 初始化进度跟踪
        self._total_windows = len(windows)
        self._completed_windows = 0

        # 创建所有任务
        logger.info(f"开始并发分析 {len(windows)} 个窗口...")
        print()  # 为进度条留出空行
        start_time = time.time()

        tasks = [
            self._analyze_single_window(idx, start, end, window_data)
            for idx, (start, end, window_data) in enumerate(windows)
        ]

        # 并发执行所有任务
        results = await asyncio.gather(*tasks)

        print()  # 进度条结束后换行
        elapsed = time.time() - start_time
        logger.info(f"全部分析完成! 总耗时: {elapsed:.2f}s, 平均: {elapsed/len(windows):.2f}s/窗口")

        # 按窗口索引排序
        results = sorted(results, key=lambda x: x["window_index"])

        return results

    def run_analysis(
        self,
        file_path: str | Path,
        max_windows: Optional[int] = None
    ) -> list[dict]:
        """
        执行滑窗分析（同步包装器）

        Args:
            file_path: 数据文件路径
            max_windows: 最大处理窗口数（用于测试限制）

        Returns:
            分析结果列表
        """
        return asyncio.run(self.run_analysis_async(file_path, max_windows))

    def save_results(self, results: list[dict], output_path: str | Path) -> None:
        """
        保存分析结果

        Args:
            results: 分析结果列表
            output_path: 输出文件路径
        """
        output_path = Path(output_path)

        output_data = {
            "analysis_time": datetime.now().isoformat(),
            "model": self._model,
            "window_config": {
                "window_size": self._window_size,
                "step_size": self._step_size,
                "max_concurrent": self._max_concurrent
            },
            "total_windows": len(results),
            "results": results
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        logger.info(f"结果已保存到: {output_path}")


def main():
    """主函数"""
    args = parse_args()

    # 确定输入文件
    if args.input_file:
        input_path = Path(args.input_file)
        if not input_path.is_absolute():
            # 尝试在多个目录中查找
            for directory in [MERGED_RESULTS_DIR, VLM_ANALYSIS_DIR]:
                candidate = directory / args.input_file
                if candidate.exists():
                    input_path = candidate
                    break
    else:
        # 自动查找活动摘要文件
        print("未指定输入文件，正在查找活动摘要文件...")
        input_path = find_activity_summary()
        if input_path is None:
            print("错误: 未找到活动摘要文件")
            print(f"  已检查: {MERGED_RESULTS_DIR}")
            print(f"  已检查: {VLM_ANALYSIS_DIR}")
            sys.exit(1)
        print(f"找到文件: {input_path}")

    if not input_path.exists():
        print(f"错误: 文件不存在: {input_path}")
        sys.exit(1)

    # 确定输出文件路径
    if args.output:
        output_path = Path(args.output)
    else:
        # 使用固定文件名，新生成的文件会覆盖旧文件
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / "sliding_window_result.json"

    # 创建分析器
    analyzer = SlidingWindowAnalyzer(
        window_size=args.window,
        step_size=args.step,
        max_concurrent=args.concurrent
    )

    # 执行分析
    print("=" * 60)
    print("       滑窗分析 (并发模式)")
    print("=" * 60)
    print(f"输入文件: {input_path.name}")
    print(f"配置: 窗口={args.window}槽({args.window * 0.5}小时), "
          f"步长={args.step}槽({args.step * 0.5}小时)")
    print(f"      并发数={args.concurrent}, "
          f"最大窗口={'不限制' if args.max_windows is None else args.max_windows}")

    # 运行分析
    results = analyzer.run_analysis(input_path, max_windows=args.max_windows)

    if not results:
        print("没有生成分析结果")
        sys.exit(1)

    # 打印结果摘要
    if not args.quiet:
        print("\n" + "=" * 60)
        print("分析结果摘要")
        print("=" * 60)

        for r in results:
            print(f"\n--- 窗口 {r['window_index'] + 1} ---")
            print(f"时间范围: {r['time_range']['start_time']} - {r['time_range']['end_time']}")
            # 只打印前500字符
            if r['analysis']:
                analysis_preview = r['analysis'][:500] + "..." if len(r['analysis']) > 500 else r['analysis']
            else:
                analysis_preview = "分析失败"
            print(f"分析预览:\n{analysis_preview}")

    # 保存完整结果
    analyzer.save_results(results, output_path)

    print("\n" + "=" * 60)
    print(f"完整结果已保存到: {output_path}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
