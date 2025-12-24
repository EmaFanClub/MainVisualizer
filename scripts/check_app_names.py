"""
检查实际应用名称格式

分析数据库中的应用名称格式，验证MetadataAnalyzer的匹配模式是否正确。
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.manictime import ManicTimeDBConnector, ActivityParser

DB_PATH = Path(r"D:\code_field\manicData\db\ManicTimeReports.db")


def main():
    parser = ActivityParser(local_timezone_hours=8)

    with ManicTimeDBConnector(DB_PATH) as db:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)

        raw_activities = db.query_activities(start_time, end_time)
        applications = db.query_applications_model()
        app_map = {app.common_id: app for app in applications}

        activities = parser.batch_parse(raw_activities, app_map)

        # 统计应用名称
        app_counter = Counter()
        for activity in activities:
            app_counter[activity.application] += 1

        print("应用名称统计 (Top 30):")
        print("-" * 60)
        for app, count in app_counter.most_common(30):
            print(f"  {app:<50} : {count}")

        print("\n应用名称格式分析:")
        with_exe = sum(1 for app in app_counter if ".exe" in app.lower())
        without_exe = len(app_counter) - with_exe
        print(f"  - 包含 .exe: {with_exe}")
        print(f"  - 不包含 .exe: {without_exe}")


if __name__ == "__main__":
    main()
