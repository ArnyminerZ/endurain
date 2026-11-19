"""API routes for live tracking sessions and contacts (authenticated)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, Security, status

import core.dependencies as core_dependencies
import core.location as core_location
import core.pagination as core_pagination
import core.rate_limit as core_rate_limit
import modules.auth.dependencies as auth_dependencies
import modules.live_tracking.schema as live_tracking_schema
import modules.live_tracking.service as live_tracking_service

# Define the API router
router = APIRouter()


@router.post(
    "/sessions",
    response_model=live_tracking_schema.LiveSessionStarted,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(auth_dependencies.check_scopes, scopes=["live:write"])],
)
@core_rate_limit.limiter.limit(core_rate_limit.WRITE)
def start_session(
    request: Request,
    response: Response,
    data: live_tracking_schema.LiveSessionStart,
    token_user_id: auth_dependencies.CurrentUserId,
    db: core_dependencies.DbSession,
) -> live_tracking_schema.LiveSessionStarted:
    """Start a live session and email the chosen contacts.

    Returns the public share link. A user can have one active session at a time.
    """
    started = live_tracking_service.start_session(token_user_id, data, db)
    core_location.set_location(response, request, "read_session", session_id=started.session.id)
    return started


@router.get(
    "/sessions/active",
    response_model=live_tracking_schema.LiveSessionOwnerView,
    dependencies=[Security(auth_dependencies.check_scopes, scopes=["live:read"])],
)
def read_active_session(
    token_user_id: auth_dependencies.CurrentUserId,
    db: core_dependencies.DbSession,
) -> live_tracking_schema.LiveSessionOwnerView:
    """Return the authenticated user's active session, its link and its track."""
    return live_tracking_service.get_active_view(token_user_id, db)


@router.get(
    "/sessions/{session_id}",
    response_model=live_tracking_schema.LiveSessionOwnerView,
    dependencies=[Security(auth_dependencies.check_scopes, scopes=["live:read"])],
)
def read_session(
    session_id: core_dependencies.UuidId,
    token_user_id: auth_dependencies.CurrentUserId,
    db: core_dependencies.DbSession,
    since: Annotated[datetime | None, Query(description="Only points recorded after this time")] = None,
) -> live_tracking_schema.LiveSessionOwnerView:
    """Watch one of the authenticated user's own sessions."""
    return live_tracking_service.get_owner_view(session_id, token_user_id, since, db)


@router.post(
    "/sessions/{session_id}/points",
    response_model=live_tracking_schema.LivePushResult,
    dependencies=[Security(auth_dependencies.check_scopes, scopes=["live:write"])],
)
@core_rate_limit.limiter.limit(core_rate_limit.LIVE_PUSH)
def push_points(
    request: Request,
    session_id: core_dependencies.UuidId,
    data: live_tracking_schema.LivePointsPush,
    token_user_id: auth_dependencies.CurrentUserId,
    db: core_dependencies.DbSession,
) -> live_tracking_schema.LivePushResult:
    """Push a batch of position updates. Resending stored points is harmless."""
    return live_tracking_service.push_points(session_id, token_user_id, data, db)


@router.post(
    "/sessions/{session_id}/stop",
    response_model=live_tracking_schema.LiveSessionRead,
    dependencies=[Security(auth_dependencies.check_scopes, scopes=["live:write"])],
)
@core_rate_limit.limiter.limit(core_rate_limit.WRITE)
def stop_session(
    request: Request,
    session_id: core_dependencies.UuidId,
    token_user_id: auth_dependencies.CurrentUserId,
    db: core_dependencies.DbSession,
) -> live_tracking_schema.LiveSessionRead:
    """Stop the session: the share link dies and the live points are deleted.

    No activity is created; the client uploads its own recording as usual.
    """
    return live_tracking_service.stop_session(session_id, token_user_id, db)


@router.delete(
    "/sessions/{session_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Security(auth_dependencies.check_scopes, scopes=["live:write"])],
)
@core_rate_limit.limiter.limit(core_rate_limit.WRITE)
def cancel_session(
    request: Request,
    session_id: core_dependencies.UuidId,
    token_user_id: auth_dependencies.CurrentUserId,
    db: core_dependencies.DbSession,
) -> None:
    """Cancel the session and delete it with its points."""
    live_tracking_service.cancel_session(session_id, token_user_id, db)


@router.get(
    "/contacts",
    response_model=live_tracking_schema.LiveContactPage,
    dependencies=[Security(auth_dependencies.check_scopes, scopes=["live:read"])],
)
def list_contacts(
    token_user_id: auth_dependencies.CurrentUserId,
    db: core_dependencies.DbSession,
    page: core_pagination.ListPage,
) -> live_tracking_schema.LiveContactPage:
    """List the people emailed when a live session starts."""
    return live_tracking_service.list_contacts(token_user_id, page.page_number, page.num_records, db)


@router.post(
    "/contacts",
    response_model=live_tracking_schema.LiveContactRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(auth_dependencies.check_scopes, scopes=["live:write"])],
)
@core_rate_limit.limiter.limit(core_rate_limit.WRITE)
def add_contact(
    request: Request,
    response: Response,
    data: live_tracking_schema.LiveContactCreate,
    token_user_id: auth_dependencies.CurrentUserId,
    db: core_dependencies.DbSession,
) -> live_tracking_schema.LiveContactRead:
    """Add a person to be emailed when a live session starts."""
    created = live_tracking_service.add_contact(token_user_id, data, db)
    core_location.set_location(response, request, "read_contact", contact_id=created.id)
    return created


@router.get(
    "/contacts/{contact_id}",
    response_model=live_tracking_schema.LiveContactRead,
    dependencies=[Security(auth_dependencies.check_scopes, scopes=["live:read"])],
)
def read_contact(
    contact_id: core_dependencies.UuidId,
    token_user_id: auth_dependencies.CurrentUserId,
    db: core_dependencies.DbSession,
) -> live_tracking_schema.LiveContactRead:
    """Read one person on the notification list."""
    return live_tracking_service.get_contact(contact_id, token_user_id, db)


@router.delete(
    "/contacts/{contact_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Security(auth_dependencies.check_scopes, scopes=["live:write"])],
)
@core_rate_limit.limiter.limit(core_rate_limit.WRITE)
def remove_contact(
    request: Request,
    contact_id: core_dependencies.UuidId,
    token_user_id: auth_dependencies.CurrentUserId,
    db: core_dependencies.DbSession,
) -> None:
    """Remove a person from the notification list."""
    live_tracking_service.remove_contact(contact_id, token_user_id, db)
