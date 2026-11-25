"""Live tracking constraints against real PostgreSQL.

The one-active-session rule is a partial unique index, and the CRUD turns its
violation into a ``ConflictError`` inside a savepoint. Both only behave like
production on a real server: SQLite ignores ``postgresql_where`` semantics for
concurrent writers and does not poison the session after a failed flush.
"""

import threading
import uuid
from datetime import UTC, datetime, timedelta

import pytest

import core.exceptions as core_exceptions
import modules.live_tracking.crud as live_tracking_crud
import modules.live_tracking.schema as live_tracking_schema
from tests._helpers.db import ensure_user

_THREADS = 6
_USER = uuid.uuid4()


def _sid(number: int) -> uuid.UUID:
    return uuid.UUID(int=number)


@pytest.fixture
def factory(pg_factory):
    ensure_user(pg_factory, _USER)
    return pg_factory


def _create(db, session_id: uuid.UUID, user_id: uuid.UUID = _USER):
    now = datetime.now(UTC)
    return live_tracking_crud.create_session(session_id, user_id, "Run", None, now, now + timedelta(hours=1), 10, db)


def test_second_active_session_conflicts_and_session_stays_usable(factory):
    with factory() as db:
        _create(db, _sid(1))
        db.commit()
        with pytest.raises(core_exceptions.ConflictError):
            _create(db, _sid(2))
        # The savepoint absorbed the failed flush: the transaction is still usable.
        assert live_tracking_crud.get_active_session_for_user(_USER, db) is not None


def test_ended_session_frees_the_slot(factory):
    with factory() as db:
        first = _create(db, _sid(1))
        live_tracking_crud.end_session(first.id, datetime.now(UTC), db)
        _create(db, _sid(2))
        db.commit()


def test_concurrent_starts_create_exactly_one_session(factory):
    barrier = threading.Barrier(_THREADS)
    outcomes: list[str] = []

    def run(index: int) -> None:
        barrier.wait()
        with factory() as db:
            try:
                _create(db, _sid(index))
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
        session = _create(db, _sid(1))
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
