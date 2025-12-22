"""
VLM连接测试脚本

使用DashScope Qwen VL API测试图像分析功能。
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.admina import QwenVLProvider
from src.ingest.manictime import ManicTimeDBConnector, ScreenshotLoader, ActivityParser


async def test_simple_connection(provider: QwenVLProvider) -> bool:
    """测试简单连接"""
    print("=" * 50)
    print("Step 1: 测试VLM连接")
    print("=" * 50)
    
    try:
        result = await provider.chat(
            messages=[{"role": "user", "content": "Reply with just OK"}],
            max_tokens=10
        )
        content = result.get("content", "")
        print(f"Response: {content}")
        print("Connection test: PASS")
        return True
    except Exception as e:
        print(f"Connection test: FAIL - {e}")
        return False


async def test_with_manictime_data(
    provider: QwenVLProvider,
    db_path: str,
    screenshots_path: str,
) -> dict:
    """使用ManicTime数据测试VLM"""
    print("\n" + "=" * 50)
    print("Step 2: 使用ManicTime数据测试VLM")
    print("=" * 50)
    
    # 初始化组件
    db = ManicTimeDBConnector(db_path)
    loader = ScreenshotLoader(screenshots_path)
    parser = ActivityParser()
    
    try:
        db.connect()
        
        # 获取数据库时间范围
        min_time, max_time = db.get_date_range()
        print(f"数据库时间范围: {min_time} - {max_time}")
        
        # 获取截图信息
        screenshot_count = loader.get_screenshot_count()
        print(f"截图目录中共有 {screenshot_count} 张截图")
        
        # 获取截图时间范围
        try:
            ss_min, ss_max = loader.get_date_range()
            print(f"截图时间范围: {ss_min} - {ss_max}")
        except Exception as e:
            print(f"获取截图时间范围失败: {e}")
            ss_min, ss_max = None, None
        
        # 使用最新的记录 - 查询最近一天的活动
        query_end = max_time
        query_start = max_time - timedelta(days=1)
        activities = db.query_activities(query_start, query_end)
        print(f"最近一天找到 {len(activities)} 条活动记录")
        
        if not activities:
            # 尝试查询更多数据
            query_start = max_time - timedelta(days=7)
            activities = db.query_activities(query_start, query_end)
            print(f"最近一周找到 {len(activities)} 条活动记录")
        
        if not activities:
            print("没有找到活动记录")
            return {}
        
        # 获取应用信息
        apps = db.query_applications_model()
        app_map = {app.common_id: app for app in apps}
        
        # 选择最新的活动记录
        selected_activity = None
        selected_screenshot = None
        
        # 按时间倒序查找
        for activity in reversed(activities):
            try:
                event = parser.parse_from_dict(
                    activity,
                    app_map.get(activity.get("group_id")),
                    None
                )
                
                # 尝试加载对应截图
                screenshot_path = loader.find_screenshot_path(
                    event.timestamp,
                    tolerance_seconds=300  # 5分钟容差
                )
                
                if screenshot_path and screenshot_path.exists():
                    selected_activity = event
                    selected_screenshot = screenshot_path
                    print(f"找到匹配截图!")
                    break
            except Exception as e:
                continue
        
        if not selected_screenshot:
            print("未找到与最新活动匹配的截图")
            # 尝试获取任意一张截图
            if ss_min and ss_max:
                for timestamp, ss_path in loader.iter_screenshots(ss_min, ss_max):
                    selected_screenshot = ss_path
                    print(f"使用第一张可用截图: {ss_path}")
                    break
        
        if not selected_screenshot:
            print("未找到可用的截图文件")
            return {}
        
        print(f"\n选中活动:")
        print(f"  时间: {selected_activity.timestamp}")
        print(f"  应用: {selected_activity.application}")
        print(f"  窗口: {selected_activity.window_title}")
        print(f"  截图: {selected_screenshot}")
        
        # 使用VLM分析截图
        print("\n正在进行VLM分析...")
        
        prompt = """分析这张屏幕截图，描述用户正在进行的活动。请以JSON格式返回：
{
    "content_type": "类型(code_editing/document_writing/browsing/communication/other)",
    "specific_activity": "具体活动描述",
    "extracted_text": "关键文本内容",
    "entities": ["识别的实体列表"],
    "confidence": 0.0-1.0
}"""
        
        result = await provider.analyze_image(
            image=selected_screenshot,
            prompt=prompt,
            max_tokens=500
        )
        
        print(f"\nVLM分析结果:")
        print(result.get("content", ""))
        print(f"\nToken使用: {result.get('usage', {})}")
        print(f"延迟: {result.get('latency_ms', 0):.0f}ms")
        
        return {
            "activity": {
                "timestamp": str(selected_activity.timestamp),
                "application": selected_activity.application,
                "window_title": selected_activity.window_title,
                "duration_seconds": selected_activity.duration_seconds,
            },
            "screenshot_path": str(selected_screenshot),
            "vlm_analysis": result.get("content", ""),
            "usage": result.get("usage", {}),
        }
        
    finally:
        db.disconnect()


async def main():
    """主测试函数"""
    # 配置
    api_key = "sk-6c514e90b3144159b4e281666f7447b1"
    model = "qwen3-vl-flash"
    
    # ManicTime路径（从环境变量或默认值）
    db_path = os.getenv(
        "MANICTIME_DB_PATH",
        r"D:\code_field\manicData\db\ManicTimeReports.db"
    )
    screenshots_path = os.getenv(
        "MANICTIME_SCREENSHOTS_PATH",
        r"Y:\临时文件\ManicTimeScreenShots"
    )
    
    print(f"使用模型: {model}")
    print(f"数据库: {db_path}")
    print(f"截图目录: {screenshots_path}")
    
    # 初始化provider
    provider = QwenVLProvider(
        api_key=api_key,
        model=model,
    )
    
    # Step 1: 简单连接测试
    if not await test_simple_connection(provider):
        print("连接测试失败，退出")
        return
    
    # Step 2: ManicTime数据测试
    result = await test_with_manictime_data(
        provider,
        db_path,
        screenshots_path,
    )
    
    if result:
        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
