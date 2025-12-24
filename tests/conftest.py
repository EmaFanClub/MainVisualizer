"""
共享测试 fixture 和配置
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

import pytest
from PIL import Image

from src.ingest.manictime.models import ActivityEvent, ActivityType


@pytest.fixture
def base_timestamp() -> datetime:
    """基准时间戳"""
    return datetime(2024, 6, 15, 14, 30, 0)


@pytest.fixture
def make_activity(base_timestamp: datetime):
    """创建 ActivityEvent 的工厂函数"""

    def _make(
        application: str = "Code.exe",
        window_title: str = "test.py - Visual Studio Code",
        duration_seconds: int = 60,
        timestamp: Optional[datetime] = None,
        is_active: bool = True,
        screenshot_path: Optional[Path] = None,
    ) -> ActivityEvent:
        return ActivityEvent(
            event_id=uuid4(),
            timestamp=timestamp or base_timestamp,
            duration_seconds=duration_seconds,
            application=application,
            window_title=window_title,
            is_active=is_active,
            activity_type=ActivityType.APPLICATION,
            screenshot_path=screenshot_path,
        )

    return _make


@pytest.fixture
def sample_activity(make_activity) -> ActivityEvent:
    """标准测试活动"""
    return make_activity()


@pytest.fixture
def make_image():
    """创建测试图像的工厂函数"""

    def _make(
        width: int = 100,
        height: int = 100,
        color: tuple = (128, 128, 128),
    ) -> Image.Image:
        return Image.new("RGB", (width, height), color)

    return _make


@pytest.fixture
def sample_image(make_image) -> Image.Image:
    """标准测试图像"""
    return make_image()


@pytest.fixture
def activity_sequence(make_activity, base_timestamp):
    """创建活动序列的工厂函数"""

    def _make(
        apps: list[str],
        interval_seconds: int = 10,
    ) -> list[ActivityEvent]:
        activities = []
        for i, app in enumerate(apps):
            ts = base_timestamp + timedelta(seconds=i * interval_seconds)
            activities.append(make_activity(
                application=app,
                timestamp=ts,
                duration_seconds=interval_seconds,
            ))
        return activities

    return _make
