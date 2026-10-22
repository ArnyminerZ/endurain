"""CRUD operations for live tracking sessions, points and contacts.

Every function flushes without committing: the service owns the transaction.
"""

from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import core.exceptions as core_exceptions
import modules.live_tracking.constants as live_tracking_constants
import modules.live_tracking.models as live_tracking_models
import modules.live_tracking.schema as live_tracking_schema
import modules.live_tracking.serializers as live_tracking_serializers

_ACTIVE = live_tracking_constants.SessionStatus.ACTIVE.value
_ENDED = live_tracking_constants.SessionStatus.ENDED.value


def create_session(
    session_id: str,
    user_id: int,
    activity_type: str,
    name: str | None,
    now: datetime,
    expires_at: datetime,
    update_interval_seconds: int,
    db: Session,
) -> live_tracking_schema.LiveSessionRead:
    """Stage a new active session.

    Args:
        session_id: The new session UUID string.
        user_id: The owner.
        activity_type: Activity type name.
        name: Optional workout name.
        now: The start time.
        expires_at: The hard deadline.
        update_interval_seconds: How often the client said it will push points.
        db: Database session.

    Returns:
        The created session.

    Raises:
        ConflictError: If the user already has an active session.
    """
    row = live_tracking_models.LiveSession(
        id=session_id,
        user_id=user_id,
        status=_ACTIVE,
        activity_type=activity_type,
        name=name,
        started_at=now,
        last_update_at=now,
        expires_at=expires_at,
        update_interval_seconds=update_interval_seconds,
    )
    try:
        with db.begin_nested():
            db.add(row)
    except IntegrityError as err:
        raise core_exceptions.ConflictError("A live session is already active") from err
    db.refresh(row)
    return live_tracking_serializers.to_session_schema(row)


def get_session(session_id: str, db: Session) -> live_tracking_schema.LiveSessionRead | None:
    """Return a session by id.

    Args:
        session_id: The session UUID string.
        db: Database session.

    Returns:
        The session, or ``None``.
    """
    row = db.get(live_tracking_models.LiveSession, session_id)
    return live_tracking_serializers.to_session_schema(row) if row is not None else None


def get_active_session_for_user(user_id: int, db: Session) -> live_tracking_schema.LiveSessionRead | None:
    """Return the user's active session, if any.

    Args:
        user_id: The owner.
        db: Database session.

    Returns:
        The active session, or ``None``.
    """
    stmt = select(live_tracking_models.LiveSession).where(
        live_tracking_models.LiveSession.user_id == user_id,
        live_tracking_models.LiveSession.status == _ACTIVE,
    )
    row = db.scalars(stmt).first()
    return live_tracking_serializers.to_session_schema(row) if row is not None else None


def count_points(session_id: str, db: Session) -> int:
    """Count a session's stored points.

    Args:
        session_id: The session UUID string.
        db: Database session.

    Returns:
        The number of points.
    """
    stmt = select(func.count()).select_from(live_tracking_models.LivePoint)
    return db.scalar(stmt.where(live_tracking_models.LivePoint.session_id == session_id)) or 0


def insert_points(
    session_id: str,
    points: list[live_tracking_schema.LivePointIn],
    now: datetime,
    db: Session,
) -> int:
    """Store the points not already stored and touch the session's last update.

    Args:
        session_id: The session UUID string.
        points: The points to store.
        now: The receive time.
        db: Database session.

    Returns:
        The number of points newly stored.
    """
    times = {point.recorded_at for point in points}
    existing_stmt = select(live_tracking_models.LivePoint.recorded_at).where(
        live_tracking_models.LivePoint.session_id == session_id,
        live_tracking_models.LivePoint.recorded_at.in_(times),
    )
    existing = {at if at.tzinfo else at.replace(tzinfo=UTC) for at in db.scalars(existing_stmt).all()}
    seen: set[datetime] = set()
    rows = []
    for point in sorted(points, key=lambda item: item.recorded_at):
        if point.recorded_at in existing or point.recorded_at in seen:
            continue
        seen.add(point.recorded_at)
        rows.append(live_tracking_models.LivePoint(session_id=session_id, **point.model_dump()))
    db.add_all(rows)
    db.execute(
        update(live_tracking_models.LiveSession)
        .where(live_tracking_models.LiveSession.id == session_id)
        .values(last_update_at=now)
    )
    db.flush()
    return len(rows)


def list_points(
    session_id: str,
    db: Session,
    *,
    since: datetime | None = None,
    limit: int = live_tracking_constants.MAX_PUBLIC_POINTS,
) -> list[live_tracking_schema.LivePointRead]:
    """Return a session's points in chronological order.

    Args:
        session_id: The session UUID string.
        db: Database session.
        since: Return only points recorded after this time.
        limit: Most points to return.

    Returns:
        The points, oldest first.
    """
    stmt = select(live_tracking_models.LivePoint).where(live_tracking_models.LivePoint.session_id == session_id)
    if since is not None:
        stmt = stmt.where(live_tracking_models.LivePoint.recorded_at > since)
    stmt = stmt.order_by(live_tracking_models.LivePoint.recorded_at).limit(limit)
    return [live_tracking_serializers.to_point_schema(row) for row in db.scalars(stmt).all()]


def get_latest_point(session_id: str, db: Session) -> live_tracking_schema.LivePointRead | None:
    """Return a session's newest point.

    Args:
        session_id: The session UUID string.
        db: Database session.

    Returns:
        The newest point, or ``None``.
    """
    stmt = (
        select(live_tracking_models.LivePoint)
        .where(live_tracking_models.LivePoint.session_id == session_id)
        .order_by(live_tracking_models.LivePoint.recorded_at.desc())
        .limit(1)
    )
    row = db.scalars(stmt).first()
    return live_tracking_serializers.to_point_schema(row) if row is not None else None


def end_session(session_id: str, ended_at: datetime, db: Session) -> None:
    """Mark a session ended, which kills its share link.

    Args:
        session_id: The session UUID string.
        ended_at: The end time.
        db: Database session.
    """
    db.execute(
        update(live_tracking_models.LiveSession)
        .where(live_tracking_models.LiveSession.id == session_id)
        .values(status=_ENDED, ended_at=ended_at)
    )
    db.flush()


def delete_points(session_id: str, db: Session) -> None:
    """Delete all of a session's points.

    Args:
        session_id: The session UUID string.
        db: Database session.
    """
    db.execute(delete(live_tracking_models.LivePoint).where(live_tracking_models.LivePoint.session_id == session_id))
    db.flush()


def delete_session(session_id: str, db: Session) -> None:
    """Delete a session and its points.

    Args:
        session_id: The session UUID string.
        db: Database session.
    """
    db.execute(delete(live_tracking_models.LivePoint).where(live_tracking_models.LivePoint.session_id == session_id))
    db.execute(delete(live_tracking_models.LiveSession).where(live_tracking_models.LiveSession.id == session_id))
    db.flush()


def list_sessions_to_finish(
    now: datetime, stale_before: datetime, db: Session
) -> list[live_tracking_schema.LiveSessionRead]:
    """Return active sessions that expired or went quiet.

    Args:
        now: The current time.
        stale_before: Sessions with no update since this time are stale.
        db: Database session.

    Returns:
        The sessions to finish server-side.
    """
    stmt = select(live_tracking_models.LiveSession).where(
        live_tracking_models.LiveSession.status == _ACTIVE,
        (live_tracking_models.LiveSession.expires_at <= now)
        | (live_tracking_models.LiveSession.last_update_at < stale_before),
    )
    return [live_tracking_serializers.to_session_schema(row) for row in db.scalars(stmt).all()]


def list_ended_sessions_before(before: datetime, db: Session) -> list[live_tracking_schema.LiveSessionRead]:
    """Return ended sessions that ended before the given time.

    Args:
        before: The retention cut-off.
        db: Database session.

    Returns:
        The ended sessions past retention.
    """
    stmt = select(live_tracking_models.LiveSession).where(
        live_tracking_models.LiveSession.status == _ENDED,
        live_tracking_models.LiveSession.ended_at < before,
    )
    return [live_tracking_serializers.to_session_schema(row) for row in db.scalars(stmt).all()]


def list_contacts(user_id: int, db: Session) -> list[live_tracking_schema.LiveContactRead]:
    """Return a user's contacts.

    Args:
        user_id: The owner.
        db: Database session.

    Returns:
        The contacts ordered by id.
    """
    stmt = (
        select(live_tracking_models.LiveContact)
        .where(live_tracking_models.LiveContact.user_id == user_id)
        .order_by(live_tracking_models.LiveContact.id)
    )
    return [live_tracking_serializers.to_contact_schema(row) for row in db.scalars(stmt).all()]


def count_contacts(user_id: int, db: Session) -> int:
    """Count a user's contacts.

    Args:
        user_id: The owner.
        db: Database session.

    Returns:
        The number of contacts.
    """
    stmt = select(func.count()).select_from(live_tracking_models.LiveContact)
    return db.scalar(stmt.where(live_tracking_models.LiveContact.user_id == user_id)) or 0


def create_contact(user_id: int, name: str, email: str, db: Session) -> live_tracking_schema.LiveContactRead:
    """Stage a new contact.

    Args:
        user_id: The owner.
        name: Display name.
        email: Email address.
        db: Database session.

    Returns:
        The created contact.

    Raises:
        ConflictError: If the user already has a contact with that email.
    """
    row = live_tracking_models.LiveContact(user_id=user_id, name=name, email=email.lower())
    try:
        with db.begin_nested():
            db.add(row)
    except IntegrityError as err:
        raise core_exceptions.ConflictError("A contact with that email already exists") from err
    db.refresh(row)
    return live_tracking_serializers.to_contact_schema(row)


def delete_contact(contact_id: int, user_id: int, db: Session) -> None:
    """Delete one of a user's contacts.

    Args:
        contact_id: The contact id.
        user_id: The owner.
        db: Database session.

    Raises:
        NotFoundError: If the user has no such contact.
    """
    result = db.execute(
        delete(live_tracking_models.LiveContact).where(
            live_tracking_models.LiveContact.id == contact_id,
            live_tracking_models.LiveContact.user_id == user_id,
        )
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise core_exceptions.NotFoundError("Contact not found")
    db.flush()
