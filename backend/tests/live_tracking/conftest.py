from datetime import UTC, datetime, timedelta

import pytest

from tests._helpers.db import create_sqlite_session

USER_ID = 7


@pytest.fixture
def db():
    session = create_sqlite_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def now():
    return datetime.now(UTC)


def point(at: datetime, lat: float = 39.0, lon: float = -0.5, **extra):
    import modules.live_tracking.schema as live_tracking_schema

    return live_tracking_schema.LivePointIn(recorded_at=at, latitude=lat, longitude=lon, **extra)


def push(points):
    import modules.live_tracking.schema as live_tracking_schema

    return live_tracking_schema.LivePointsPush(points=points)


def track(now: datetime, count: int = 3):
    base = now - timedelta(seconds=count * 10)
    return [point(base + timedelta(seconds=10 * i), 39.0 + i * 0.001, -0.5, heart_rate=120 + i) for i in range(count)]
