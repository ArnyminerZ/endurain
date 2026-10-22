"""Application logic for live tracking.

Owns the transaction for every write. The share link is derived, not stored (see
:mod:`modules.live_tracking.share_token`), so the link dies simply because the
session is no longer active.

A session ends in one of three ways, all through :func:`_end_session`: the
owner stops it, the owner cancels it, or the scheduler ends it because it
expired or went quiet. Live data is never turned into an activity: the client
uploads its own recording through the normal upload when the workout is done,
so ending a session only kills the link and deletes the live points.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jasil.providers as platform_providers
from sqlalchemy.orm import Session

import core.config as core_config
import core.exceptions as core_exceptions
import core.i18n as core_i18n
import core.logger as core_logger
import core.mail as core_mail
import modules.live_tracking.constants as live_tracking_constants
import modules.live_tracking.crud as live_tracking_crud
import modules.live_tracking.email_messages as live_tracking_email_messages
import modules.live_tracking.event_publishers as live_tracking_event_publishers
import modules.live_tracking.schema as live_tracking_schema
import modules.live_tracking.share_token as live_tracking_share_token
import modules.users.users.integration_service as users_integration

logger = core_logger.get_logger(__name__)

_SESSION_NOT_FOUND = "Live session not found"


def _now() -> datetime:
    """Return the current UTC time.

    Returns:
        A timezone-aware ``datetime``.
    """
    return datetime.now(UTC)


def _ensure_enabled() -> None:
    """Raise unless the feature is enabled on this server.

    Raises:
        ServiceUnavailableError: When ``LIVE_TRACKING_ENABLED`` is false.
    """
    if not core_config.settings.LIVE_TRACKING_ENABLED:
        raise core_exceptions.ServiceUnavailableError("Live tracking is disabled on this server")


def _secret() -> str:
    """Return the server secret share tokens are keyed with.

    Returns:
        The ``SECRET_KEY`` value.
    """
    return core_config.read_secret("SECRET_KEY") or ""


def share_url(session_id: str) -> str:
    """Return the public link for a session.

    Args:
        session_id: The session UUID string.

    Returns:
        The frontend URL that viewers open.
    """
    token = live_tracking_share_token.build_token(session_id, _secret())
    return f"{core_config.settings.ENDURAIN_HOST}/live/{token}"


def _get_owned_session(session_id: str, user_id: int, db: Session) -> live_tracking_schema.LiveSessionRead:
    """Return a session the user owns, answering like a missing one otherwise.

    Args:
        session_id: The session UUID string.
        user_id: The authenticated user.
        db: Database session.

    Returns:
        The session.

    Raises:
        AccessConcealedError: When it does not exist or belongs to someone else.
    """
    session = live_tracking_crud.get_session(session_id, db)
    if session is None or session.user_id != user_id:
        logger.warning(
            "Denied access to a live session",
            extra=core_logger.context(user_id=user_id, session_id=session_id),
        )
        raise core_exceptions.AccessConcealedError(_SESSION_NOT_FOUND)
    return session


def start_session(
    user_id: int, data: live_tracking_schema.LiveSessionStart, db: Session
) -> live_tracking_schema.LiveSessionStarted:
    """Start a live session and queue the contact notification emails.

    Args:
        user_id: The authenticated user.
        data: The start request.
        db: Database session.

    Returns:
        The session and its share link. The session starts even when email is
        unavailable; ``notified_contacts`` says how many emails were queued.

    Raises:
        ServiceUnavailableError: When the feature is disabled.
        ConflictError: When the user already has an active session.
        InvalidInputError: When a requested contact does not exist.
    """
    _ensure_enabled()
    if live_tracking_crud.get_active_session_for_user(user_id, db) is not None:
        raise core_exceptions.ConflictError("A live session is already active")

    contacts = live_tracking_crud.list_contacts(user_id, db)
    if data.notify_contact_ids is not None:
        known = {contact.id for contact in contacts}
        if not set(data.notify_contact_ids) <= known:
            raise core_exceptions.InvalidInputError("Unknown contact id")
        contact_ids = sorted(set(data.notify_contact_ids))
    else:
        contact_ids = [contact.id for contact in contacts]

    now = _now()
    session = live_tracking_crud.create_session(
        str(uuid.uuid4()),
        user_id,
        data.activity_type,
        data.name,
        now,
        now + timedelta(hours=core_config.settings.LIVE_TRACKING_MAX_SESSION_HOURS),
        data.update_interval_seconds,
        db,
    )
    email_enabled = core_mail.is_mail_configured()
    notified = contact_ids if email_enabled else []
    if notified:
        live_tracking_event_publishers.publish_live_session_started(user_id, session.id, notified, db, commit=db.commit)
    else:
        db.commit()
    logger.info(
        "Live session started",
        extra=core_logger.context(user_id=user_id, session_id=session.id, notified=len(notified)),
    )
    return live_tracking_schema.LiveSessionStarted(
        session=session,
        share_url=share_url(session.id),
        notified_contacts=len(notified),
        email_enabled=email_enabled,
    )


def push_points(
    session_id: str, user_id: int, data: live_tracking_schema.LivePointsPush, db: Session
) -> live_tracking_schema.LivePushResult:
    """Store a batch of points on the user's active session.

    Args:
        session_id: The session UUID string.
        user_id: The authenticated user.
        data: The points. Resending stored points is harmless.
        db: Database session.

    Returns:
        How many points were new and the session's total.

    Raises:
        AccessConcealedError: When the session is not the user's.
        ConflictError: When the session already ended.
        InvalidInputError: When a point has no timezone or an implausible time,
            or the session is full.
    """
    session = _get_owned_session(session_id, user_id, db)
    if session.status != live_tracking_constants.SessionStatus.ACTIVE:
        raise core_exceptions.ConflictError("The live session has ended")

    now = _now()
    latest = now + live_tracking_constants.MAX_POINT_FUTURE_SKEW
    earliest = session.started_at - live_tracking_constants.MAX_POINT_BEFORE_START
    for point in data.points:
        if point.recorded_at.tzinfo is None:
            raise core_exceptions.InvalidInputError("recorded_at must include a timezone")
        if not earliest <= point.recorded_at <= latest:
            raise core_exceptions.InvalidInputError("recorded_at is outside the session window")

    total = live_tracking_crud.count_points(session_id, db)
    if total + len(data.points) > live_tracking_constants.MAX_POINTS_PER_SESSION:
        raise core_exceptions.InvalidInputError("The live session has too many points")

    accepted = live_tracking_crud.insert_points(session_id, data.points, now, db)
    db.commit()
    logger.debug(
        "Live points stored",
        extra=core_logger.context(session_id=session_id, accepted=accepted, total_points=total + accepted),
    )
    return live_tracking_schema.LivePushResult(accepted=accepted, total_points=total + accepted)


def get_owner_view(
    session_id: str, user_id: int, since: datetime | None, db: Session
) -> live_tracking_schema.LiveSessionOwnerView:
    """Return a session the user owns with its points and link.

    Args:
        session_id: The session UUID string.
        user_id: The authenticated user.
        since: Return only points recorded after this time.
        db: Database session.

    Returns:
        The owner's view.

    Raises:
        AccessConcealedError: When the session is not the user's.
    """
    session = _get_owned_session(session_id, user_id, db)
    points = live_tracking_crud.list_points(session_id, db, since=since)
    return live_tracking_schema.LiveSessionOwnerView(session=session, share_url=share_url(session_id), points=points)


def get_active_view(user_id: int, db: Session) -> live_tracking_schema.LiveSessionOwnerView:
    """Return the user's active session.

    Args:
        user_id: The authenticated user.
        db: Database session.

    Returns:
        The owner's view of the active session.

    Raises:
        NotFoundError: When the user has no active session.
    """
    session = live_tracking_crud.get_active_session_for_user(user_id, db)
    if session is None:
        raise core_exceptions.NotFoundError("No active live session")
    return get_owner_view(session.id, user_id, None, db)


def _end_session(session: live_tracking_schema.LiveSessionRead, db: Session) -> live_tracking_schema.LiveSessionRead:
    """End a session: the share link dies and its live points are deleted.

    No activity is created from the live data. The client records the workout
    itself and uploads it through the normal activity upload when it is done.
    Ending an already ended session is a no-op, so a retried stop is harmless.

    Args:
        session: The session to end.
        db: Database session.

    Returns:
        The ended session.
    """
    if session.status == live_tracking_constants.SessionStatus.ACTIVE:
        live_tracking_crud.end_session(session.id, _now(), db)
    live_tracking_crud.delete_points(session.id, db)
    db.commit()
    logger.info("Live session ended", extra=core_logger.context(user_id=session.user_id, session_id=session.id))
    return live_tracking_crud.get_session(session.id, db) or session


def stop_session(session_id: str, user_id: int, db: Session) -> live_tracking_schema.LiveSessionRead:
    """Stop the user's session; the share link stops working and the live points are deleted.

    Args:
        session_id: The session UUID string.
        user_id: The authenticated user.
        db: Database session.

    Returns:
        The ended session.

    Raises:
        AccessConcealedError: When the session is not the user's.
    """
    return _end_session(_get_owned_session(session_id, user_id, db), db)


def cancel_session(session_id: str, user_id: int, db: Session) -> None:
    """Delete the user's session and its points.

    Args:
        session_id: The session UUID string.
        user_id: The authenticated user.
        db: Database session.

    Raises:
        AccessConcealedError: When the session is not the user's.
    """
    _get_owned_session(session_id, user_id, db)
    live_tracking_crud.delete_session(session_id, db)
    db.commit()
    logger.info("Live session cancelled", extra=core_logger.context(user_id=user_id, session_id=session_id))


def finish_stale_sessions(db: Session) -> int:
    """End sessions that expired or went quiet and purge old ended ones.

    Args:
        db: Database session.

    Returns:
        How many active sessions were ended.
    """
    now = _now()
    stale_before = now - timedelta(minutes=core_config.settings.LIVE_TRACKING_STALE_MINUTES)
    finished = 0
    for session in live_tracking_crud.list_sessions_to_finish(now, stale_before, db):
        try:
            _end_session(session, db)
            finished += 1
        except Exception as err:
            db.rollback()
            logger.error(
                "Could not finish a stale live session",
                exc_info=err,
                extra=core_logger.context(session_id=session.id),
            )
    for session in live_tracking_crud.list_ended_sessions_before(now - live_tracking_constants.ENDED_RETENTION, db):
        live_tracking_crud.delete_session(session.id, db)
    db.commit()
    return finished


def get_public_view(token: str, since: datetime | None, db: Session) -> live_tracking_schema.PublicLiveView:
    """Return what an anonymous viewer of a share link sees.

    Args:
        token: The share token from the link.
        since: Return only points recorded after this time.
        db: Database session.

    Returns:
        The athlete's first name, session metadata, latest point and track.

    Raises:
        NotFoundError: For a forged, unknown, ended or expired link, all answered
            identically so the endpoint cannot be used to probe sessions.
    """
    if not core_config.settings.LIVE_TRACKING_ENABLED:
        raise core_exceptions.NotFoundError(_SESSION_NOT_FOUND)
    session_id = live_tracking_share_token.parse_token(token, _secret())
    session = live_tracking_crud.get_session(session_id, db) if session_id else None
    if (
        session is None
        or session.status != live_tracking_constants.SessionStatus.ACTIVE
        or session.expires_at <= _now()
    ):
        raise core_exceptions.NotFoundError(_SESSION_NOT_FOUND)

    user = users_integration.get_user(session.user_id, db)
    athlete = (user.name or "").split(" ")[0] if user is not None else ""
    return live_tracking_schema.PublicLiveView(
        athlete=athlete or "Athlete",
        activity_type=session.activity_type,
        name=session.name,
        started_at=session.started_at,
        last_update_at=session.last_update_at,
        update_interval_seconds=session.update_interval_seconds,
        latest=live_tracking_crud.get_latest_point(session.id, db),
        points=live_tracking_crud.list_points(session.id, db, since=since),
        total_points=live_tracking_crud.count_points(session.id, db),
    )


def list_contacts(user_id: int, db: Session) -> list[live_tracking_schema.LiveContactRead]:
    """Return the user's contacts.

    Args:
        user_id: The authenticated user.
        db: Database session.

    Returns:
        The contacts.
    """
    return live_tracking_crud.list_contacts(user_id, db)


def add_contact(
    user_id: int, data: live_tracking_schema.LiveContactCreate, db: Session
) -> live_tracking_schema.LiveContactRead:
    """Add a contact to the user's list.

    Args:
        user_id: The authenticated user.
        data: The contact.
        db: Database session.

    Returns:
        The created contact.

    Raises:
        ConflictError: When the email is already a contact.
        InvalidInputError: When the user has the maximum number of contacts.
    """
    if live_tracking_crud.count_contacts(user_id, db) >= core_config.settings.LIVE_TRACKING_MAX_CONTACTS:
        raise core_exceptions.InvalidInputError("Too many live tracking contacts")
    contact = live_tracking_crud.create_contact(user_id, data.name, data.email, db)
    db.commit()
    logger.info("Live tracking contact added", extra=core_logger.context(user_id=user_id, contact_id=contact.id))
    return contact


def remove_contact(contact_id: int, user_id: int, db: Session) -> None:
    """Remove one of the user's contacts.

    Args:
        contact_id: The contact id.
        user_id: The authenticated user.
        db: Database session.

    Raises:
        NotFoundError: When the user has no such contact.
    """
    live_tracking_crud.delete_contact(contact_id, user_id, db)
    db.commit()
    logger.info("Live tracking contact removed", extra=core_logger.context(user_id=user_id, contact_id=contact_id))


def send_session_started_emails(
    session_id: str, contact_ids: list[int], mail: platform_providers.MailProvider, db: Session
) -> int:
    """Email the share link to the chosen contacts of a session that just started.

    Skips silently when the session already ended: a delayed email with a dead
    link would only confuse the recipient.

    Args:
        session_id: The session UUID string.
        contact_ids: The contacts to notify.
        mail: The platform mail provider.
        db: Database session.

    Returns:
        How many emails were handed to the mail server.

    Raises:
        MailError: After trying every contact, when a delivery failed transiently,
            so the durable job is retried.
    """
    session = live_tracking_crud.get_session(session_id, db)
    if session is None or session.status != live_tracking_constants.SessionStatus.ACTIVE:
        return 0
    user = users_integration.get_user(session.user_id, db)
    if user is None:
        return 0

    link = share_url(session.id)
    locale = core_i18n.normalize_locale(user.preferred_language)
    wanted = set(contact_ids)
    sent = 0
    failure: platform_providers.MailError | None = None
    for contact in live_tracking_crud.list_contacts(session.user_id, db):
        if contact.id not in wanted:
            continue
        subject, html_content, text_content = live_tracking_email_messages.get_live_session_started_email(
            contact.name, user.name, session.name, link, core_config.settings.ENDURAIN_HOST, locale
        )
        try:
            if core_mail.send_email(mail, contact.email, subject, html_content, text_content):
                sent += 1
        except platform_providers.MailError as err:
            failure = err
    if failure is not None:
        raise failure
    return sent
