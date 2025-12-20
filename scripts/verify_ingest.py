"""
ManicTime 数据摄入验证脚本

验证ManicTime数据读取和解析功能是否正常工作。
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core import setup_logging, get_logger
from src.ingest.manictime import (
    ManicTimeDBConnector,
    ScreenshotLoader,
    ActivityParser,
)

# 配置日志
setup_logging()
logger = get_logger(__name__)

# 配置路径（从环境变量或默认值）
DB_PATH = os.environ.get(
    "MANICTIME_DB_PATH",
    r"D:\code_field\manicData\db\ManicTimeReports.db"
)
SCREENSHOTS_PATH = os.environ.get(
    "MANICTIME_SCREENSHOTS_PATH", 
    r"Y:\临时文件\ManicTimeScreenShots"
)


def verify_database_connection():
    """验证数据库连接"""
    print("\n" + "=" * 60)
    print("1. 验证数据库连接")
    print("=" * 60)
    
    connector = ManicTimeDBConnector(DB_PATH)
    
    try:
        connector.connect()
        print(f"[PASS] 数据库连接成功: {DB_PATH}")
        
        # 获取基本统计
        count = connector.get_activity_count()
        print(f"[PASS] 活动记录总数: {count}")
        
        date_range = connector.get_date_range()
        print(f"[PASS] 数据时间范围: {date_range[0]} ~ {date_range[1]}")
        
        return True
    except Exception as e:
        print(f"[FAIL] 数据库连接失败: {e}")
        return False
    finally:
        connector.disconnect()


def verify_activity_query():
    """验证活动查询"""
    print("\n" + "=" * 60)
    print("2. 验证活动查询")
    print("=" * 60)
    
    with ManicTimeDBConnector(DB_PATH) as connector:
        # 获取数据库中的实际日期范围
        min_time, max_time = connector.get_date_range()
        
        if max_time:
            # 查询数据库中最后7天的活动（而非当前日期）
            end_time = max_time
            start_time = end_time - timedelta(days=7)
            
            activities = connector.query_activities(start_time, end_time)
            print(f"[PASS] 数据库最后7天活动记录: {len(activities)} 条")
            print(f"  查询范围: {start_time.date()} ~ {end_time.date()}")
            
            if activities:
                print("\n样本数据 (前3条):")
                for i, act in enumerate(activities[:3]):
                    print(f"  [{i+1}] {act.get('app_name', 'Unknown')}")
                    print(f"      开始: {act.get('start_utc_time')}")
                    print(f"      结束: {act.get('end_utc_time')}")
        else:
            print("[FAIL] 无法获取数据库日期范围")
            return False
        
        return len(activities) > 0


def verify_application_query():
    """验证应用列表查询"""
    print("\n" + "=" * 60)
    print("3. 验证应用列表查询")
    print("=" * 60)
    
    with ManicTimeDBConnector(DB_PATH) as connector:
        apps = connector.query_applications_model()
        print(f"[PASS] 应用总数: {len(apps)}")
        
        if apps:
            print("\n前5个应用:")
            for app in apps[:5]:
                title = app.window_title[:50] if app.window_title else 'N/A'
                print(f"  - {app.application_name}: {title}")
        
        return True


def verify_day_summary():
    """验证日汇总查询"""
    print("\n" + "=" * 60)
    print("4. 验证日汇总查询")
    print("=" * 60)
    
    from datetime import date
    
    with ManicTimeDBConnector(DB_PATH) as connector:
        # 查询昨天的汇总
        yesterday = date.today() - timedelta(days=1)
        summary = connector.query_day_summary_model(yesterday)
        
        print(f"[PASS] 日期: {summary.summary_date}")
        print(f"[PASS] 总活跃时长: {summary.total_active_hours:.2f} 小时")
        print(f"[PASS] 应用数量: {len(summary.application_stats)}")
        
        if summary.top_applications:
            print("\nTop 5 应用:")
            for app, seconds in summary.top_applications[:5]:
                hours = seconds / 3600
                print(f"  - {app}: {hours:.2f} 小时")
        
        return True


def verify_screenshot_loader():
    """验证截图加载器"""
    print("\n" + "=" * 60)
    print("5. 验证截图加载器")
    print("=" * 60)
    
    screenshots_path = Path(SCREENSHOTS_PATH)
    if not screenshots_path.exists():
        print(f"[FAIL] 截图目录不存在: {screenshots_path}")
        return False
    
    loader = ScreenshotLoader(screenshots_path)
    
    # 构建索引
    count = loader.get_screenshot_count()
    print(f"[PASS] 截图总数: {count}")
    
    date_range = loader.get_date_range()
    if date_range[0]:
        print(f"[PASS] 截图时间范围: {date_range[0]} ~ {date_range[1]}")
    
    # 尝试加载最近的截图
    if date_range[1]:
        metadata = loader.get_metadata(date_range[1], tolerance_seconds=3600)
        if metadata:
            print(f"\n最新截图信息:")
            print(f"  - 时间: {metadata.timestamp}")
            print(f"  - 尺寸: {metadata.width} x {metadata.height}")
            print(f"  - 路径: {metadata.file_path.name}")
    
    return True


def verify_activity_parser():
    """验证活动解析器"""
    print("\n" + "=" * 60)
    print("6. 验证活动解析器")
    print("=" * 60)
    
    parser = ActivityParser()
    
    with ManicTimeDBConnector(DB_PATH) as connector:
        # 获取数据库中的实际日期范围
        min_time, max_time = connector.get_date_range()
        
        if not max_time:
            print("[FAIL] 无法获取数据库日期范围")
            return False
        
        # 查询数据库中最后1天的活动
        end_time = max_time
        start_time = end_time - timedelta(days=1)
        
        raw_activities = connector.query_activities(start_time, end_time)
        
        if not raw_activities:
            print("[FAIL] 没有找到活动记录")
            return False
        
        # 获取应用信息映射
        apps = connector.query_applications_model()
        app_map = {app.common_id: app for app in apps}
        
        # 批量解析
        events = parser.batch_parse(raw_activities, app_map)
        print(f"[PASS] 成功解析 {len(events)} 条活动记录")
        
        if events:
            print("\n样本事件 (前3条):")
            for i, event in enumerate(events[:3]):
                print(f"  [{i+1}] {event.application}")
                title = event.window_title[:50] if event.window_title else 'N/A'
                print(f"      窗口: {title}")
                print(f"      时长: {event.duration_seconds} 秒")
                print(f"      类型: {event.activity_type.value}")
        
        return True


def main():
    """运行所有验证"""
    print("=" * 60)
    print("ManicTime 数据摄入验证")
    print("=" * 60)
    print(f"\n数据库路径: {DB_PATH}")
    print(f"截图路径: {SCREENSHOTS_PATH}")
    
    results = {
        "数据库连接": verify_database_connection(),
        "活动查询": verify_activity_query(),
        "应用列表": verify_application_query(),
        "日汇总": verify_day_summary(),
        "截图加载器": verify_screenshot_loader(),
        "活动解析器": verify_activity_parser(),
    }
    
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: [{status}]")
        if not passed:
            all_passed = False
    
    print("\n" + ("所有验证通过!" if all_passed else "部分验证失败"))
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
