"""
VLM集成测试 - 结合ManicTime活动数据和截图

将活动数据库信息（窗口名称、应用名称等）与截图一起发送给VLM进行分析。
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.admina import QwenVLProvider
from src.ingest.manictime import ManicTimeDBConnector


async def main():
    # 配置 - API key 从环境变量获取
    import os
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("Error: DASHSCOPE_API_KEY environment variable not set")
        return
    
    model = "qwen3-vl-flash"
    db_path = r"D:\code_field\manicData\db\ManicTimeReports.db"
    screenshots_path = r"Y:\临时文件\ManicTimeScreenShots"
    
    # 使用 2025-10-23 的截图，应该在数据库时间范围内
    screenshot_date = "2025-10-23"
    screenshot_file = "2025-10-23_21-58-16_08-00_1704_1341_755811_0.jpg"
    screenshot_path = Path(screenshots_path) / screenshot_date / screenshot_file
    
    print(f"截图路径: {screenshot_path}")
    print(f"截图存在: {screenshot_path.exists()}")
    
    # 从文件名解析时间戳 (UTC+8)
    parts = screenshot_file.split("_")
    date_str = parts[0]
    time_str = parts[1]
    # 截图时间是本地时间 UTC+8，转换为 UTC
    local_time = datetime.strptime(f"{date_str} {time_str.replace('-', ':')}", "%Y-%m-%d %H:%M:%S")
    utc_time = local_time - timedelta(hours=8)  # 转换为UTC
    print(f"截图本地时间: {local_time}")
    print(f"截图UTC时间: {utc_time}")
    
    # 连接数据库查询对应时间的活动
    db = ManicTimeDBConnector(db_path)
    
    try:
        db.connect()
        
        # 查询截图时间附近的活动（UTC时间，前后5分钟）
        start_time = utc_time - timedelta(minutes=5)
        end_time = utc_time + timedelta(minutes=5)
        activities = db.query_activities(start_time, end_time)
        print(f"找到 {len(activities)} 条相关活动")
        
        # 找到最接近截图时间的活动
        closest_activity = None
        min_diff = timedelta(hours=1)
        
        for act in activities:
            act_start = datetime.strptime(act["start_utc_time"], "%Y-%m-%d %H:%M:%S")
            diff = abs(act_start - utc_time)
            if diff < min_diff:
                min_diff = diff
                closest_activity = act
        
        if closest_activity:
            app_name = closest_activity.get("app_name", "未知")
            group_name = closest_activity.get("group_name", "未知")
            start_utc = closest_activity.get("start_utc_time", "")
            end_utc = closest_activity.get("end_utc_time", "")
            
            # 计算持续时间
            if start_utc and end_utc:
                s = datetime.strptime(start_utc, "%Y-%m-%d %H:%M:%S")
                e = datetime.strptime(end_utc, "%Y-%m-%d %H:%M:%S")
                duration = (e - s).total_seconds()
            else:
                duration = 0
            
            print(f"\n匹配的活动记录:")
            print(f"  应用: {app_name}")
            print(f"  窗口: {group_name}")
            print(f"  开始时间(UTC): {start_utc}")
            print(f"  持续时间: {duration}s")
            
            # 构建发送给VLM的上下文信息
            context = f"""以下是用户活动的上下文信息：
- 应用程序: {app_name}
- 窗口/组名: {group_name}
- 活动时间(UTC): {start_utc}
- 活动持续时间: {duration}秒

请结合上述信息和截图，详细描述用户正在进行的活动，包括：
1. 用户正在使用什么软件
2. 具体在做什么任务
3. 屏幕上显示的关键内容"""
        else:
            print("未找到匹配的活动记录")
            return
        
    finally:
        db.disconnect()
    
    # 初始化VLM并分析
    print("\n正在调用VLM进行分析...")
    provider = QwenVLProvider(api_key=api_key, model=model)
    
    result = await provider.analyze_image(
        image=screenshot_path,
        prompt=context,
        max_tokens=600
    )
    
    print(f"\n{'='*60}")
    print("VLM分析结果:")
    print('='*60)
    print(result["content"])
    print(f"\nToken使用: {result.get('usage', {})}")
    print(f"延迟: {result.get('latency_ms', 0):.0f}ms")


if __name__ == "__main__":
    asyncio.run(main())
