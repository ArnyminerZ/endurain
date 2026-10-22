"""Publish the live tracking domain events through the platform publish facade."""

from collections.abc import Callable

import jasil.publisher as platform_publisher
from sqlalchemy.orm import Session

import core.event_metadata as core_event_metadata
import modules.live_tracking.events as live_tracking_events


def publish_live_session_started(
    user_id: int,
    session_id: str,
    contact_ids: list[int],
    db: Session,
    *,
    commit: Callable[[], None],
) -> None:
    """Publish ``live_tracking.session_started`` after a session row is created.

    Args:
        user_id: The session owner, mirrored into the metadata for correlation.
        session_id: The session that started.
        contact_ids: The contacts to notify.
        db: The producer's DB session, used for durable outbox delivery.
        commit: Commit the session row and outbox event together.
    """
    payload = live_tracking_events.LiveSessionStartedPayload(session_id=session_id, contact_ids=contact_ids)
    platform_publisher.publish_committing(
        live_tracking_events.LIVE_SESSION_STARTED,
        payload.model_dump(),
        source="api:start_live_session",
        metadata={core_event_metadata.META_USER_ID: user_id},
        db=db,
        commit=commit,
        schema_version=payload.SCHEMA_VERSION,
    )
