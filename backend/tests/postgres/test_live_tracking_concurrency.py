"""Live tracking constraints against real PostgreSQL.

The one-active-session rule is a partial unique index, and the CRUD turns its
violation into a ``ConflictError`` inside a savepoint. Both only behave like
production on a real server: SQLite ignores ``postgresql_where`` semantics for
concurrent writers and does not poison the session after a failed flush.
"""

import threading
from datetime import UTC, datetime, timedelta

import pytest

import core.exceptions as core_exceptions
import modules.live_tracking.crud as live_tracking_crud
import modules.live_tracking.schema as live_tracking_schema
from tests._helpers.db import ensure_user

_THREADS = 6


@pytest.fixture
def factory(pg_factory):
    ensure_user(pg_factory, 1)
    return pg_factory


def _create(db, session_id: str, user_id: int = 1):
    now = datetime.now(UTC)
    return live_tracking_crud.create_session(session_id, user_id, "Run", None, now, now + timedelta(hours=1), db)


def test_second_active_session_conflicts_and_session_stays_usable(factory):
    with factory() as db:
        _create(db, "00000000-0000-4000-8000-000000000001")
        db.commit()
        with pytest.raises(core_exceptions.ConflictError):
            _create(db, "00000000-0000-4000-8000-000000000002")
        # The savepoint absorbed the failed flush: the transaction is still usable.
        assert live_tracking_crud.get_active_session_for_user(1, db) is not None


def test_ended_session_frees_the_slot(factory):
    with factory() as db:
        first = _create(db, "00000000-0000-4000-8000-000000000001")
        live_tracking_crud.end_session(first.id, datetime.now(UTC), db)
        _create(db, "00000000-0000-4000-8000-000000000002")
        db.commit()


def test_concurrent_starts_create_exactly_one_session(factory):
    barrier = threading.Barrier(_THREADS)
    outcomes: list[str] = []

    def run(index: int) -> None:
        barrier.wait()
        with factory() as db:
            try:
                _create(db, f"00000000-0000-4000-8000-{index:012d}")
                db.commit()
                outcomes.append("created")
            except core_exceptions.ConflictError:
                db.rollback()
                outcomes.append("conflict")

    threads = [threading.Thread(target=run, args=(i,)) for i in range(1, _THREADS + 1)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["conflict"] * (_THREADS - 1) + ["created"]


def test_points_are_deduplicated_and_cascade_with_the_session(factory):
    now = datetime.now(UTC)
    with factory() as db:
        session = _create(db, "00000000-0000-4000-8000-000000000001")
        batch = [
            live_tracking_schema.LivePointIn(recorded_at=now - timedelta(seconds=i), latitude=1.0, longitude=2.0)
            for i in range(3)
        ]
        assert live_tracking_crud.insert_points(session.id, batch, now, db) == 3
        assert live_tracking_crud.insert_points(session.id, batch + batch, now, db) == 0
        db.commit()
        live_tracking_crud.delete_session(session.id, db)
        db.commit()
        assert live_tracking_crud.count_points(session.id, db) == 0
