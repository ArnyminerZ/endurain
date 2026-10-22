"""API routes for live tracking sessions and contacts (authenticated)."""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Security, status
from sqlalchemy.orm import Session

import core.database as core_database
import core.dependencies as core_dependencies
import core.rate_limit as core_rate_limit
import modules.auth.dependencies as auth_dependencies
import modules.live_tracking.schema as live_tracking_schema
import modules.live_tracking.service as live_tracking_service

# Define the API router
router = APIRouter()

SessionId = Annotated[
    str,
    Path(
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        description="Live session UUID",
    ),
]


@router.post(
    "/sessions",
    response_model=live_tracking_schema.LiveSessionStarted,
    status_code=status.HTTP_201_CREATED,
)
@core_rate_limit.limiter.limit(core_rate_limit.WRITE)
def start_session(
    request: Request,
    data: live_tracking_schema.LiveSessionStart,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_scopes, scopes=["live:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_sub_from_access_token)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> live_tracking_schema.LiveSessionStarted:
    """Start a live session and email the chosen contacts.

    Returns the public share link. A user can have one active session at a time.
    """
    return live_tracking_service.start_session(token_user_id, data, db)


@router.get(
    "/sessions/active",
    response_model=live_tracking_schema.LiveSessionOwnerView,
)
def read_active_session(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_scopes, scopes=["live:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_sub_from_access_token)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> live_tracking_schema.LiveSessionOwnerView:
    """Return the authenticated user's active session, its link and its track."""
    return live_tracking_service.get_active_view(token_user_id, db)


@router.get(
    "/sessions/{session_id}",
    response_model=live_tracking_schema.LiveSessionOwnerView,
)
def read_session(
    session_id: SessionId,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_scopes, scopes=["live:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_sub_from_access_token)],
    db: Annotated[Session, Depends(core_database.get_db)],
    since: Annotated[datetime | None, Query(description="Only points recorded after this time")] = None,
) -> live_tracking_schema.LiveSessionOwnerView:
    """Watch one of the authenticated user's own sessions."""
    return live_tracking_service.get_owner_view(session_id, token_user_id, since, db)


@router.post(
    "/sessions/{session_id}/points",
    response_model=live_tracking_schema.LivePushResult,
)
@core_rate_limit.limiter.limit(core_rate_limit.LIVE_PUSH)
def push_points(
    request: Request,
    session_id: SessionId,
    data: live_tracking_schema.LivePointsPush,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_scopes, scopes=["live:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_sub_from_access_token)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> live_tracking_schema.LivePushResult:
    """Push a batch of position updates. Resending stored points is harmless."""
    return live_tracking_service.push_points(session_id, token_user_id, data, db)


@router.post(
    "/sessions/{session_id}/stop",
    response_model=live_tracking_schema.LiveSessionStopped,
)
@core_rate_limit.limiter.limit(core_rate_limit.WRITE)
def stop_session(
    request: Request,
    session_id: SessionId,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_scopes, scopes=["live:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_sub_from_access_token)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> live_tracking_schema.LiveSessionStopped:
    """Stop the session: the share link dies and the track becomes an activity.

    If the activity could not be created the points are kept; calling stop again
    retries.
    """
    return live_tracking_service.stop_session(session_id, token_user_id, db)


@router.delete(
    "/sessions/{session_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
@core_rate_limit.limiter.limit(core_rate_limit.WRITE)
def cancel_session(
    request: Request,
    session_id: SessionId,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_scopes, scopes=["live:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_sub_from_access_token)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> None:
    """Cancel the session and delete its points without creating an activity."""
    live_tracking_service.cancel_session(session_id, token_user_id, db)


@router.get(
    "/contacts",
    response_model=list[live_tracking_schema.LiveContactRead],
)
def list_contacts(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_scopes, scopes=["live:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_sub_from_access_token)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> list[live_tracking_schema.LiveContactRead]:
    """List the people emailed when a live session starts."""
    return live_tracking_service.list_contacts(token_user_id, db)


@router.post(
    "/contacts",
    response_model=live_tracking_schema.LiveContactRead,
    status_code=status.HTTP_201_CREATED,
)
@core_rate_limit.limiter.limit(core_rate_limit.WRITE)
def add_contact(
    request: Request,
    data: live_tracking_schema.LiveContactCreate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_scopes, scopes=["live:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_sub_from_access_token)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> live_tracking_schema.LiveContactRead:
    """Add a person to be emailed when a live session starts."""
    return live_tracking_service.add_contact(token_user_id, data, db)


@router.delete(
    "/contacts/{contact_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
@core_rate_limit.limiter.limit(core_rate_limit.WRITE)
def remove_contact(
    request: Request,
    contact_id: core_dependencies.PositiveId,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_scopes, scopes=["live:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_sub_from_access_token)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> None:
    """Remove a person from the notification list."""
    live_tracking_service.remove_contact(contact_id, token_user_id, db)
