"""FastAPI routes for live tracking (public, unauthenticated)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response
from sqlalchemy.orm import Session

import core.database as core_database
import core.rate_limit as core_rate_limit
import modules.live_tracking.schema as live_tracking_schema
import modules.live_tracking.service as live_tracking_service

# Define the API router
router = APIRouter()


@router.get(
    "/{token}",
    response_model=live_tracking_schema.PublicLiveView,
)
@core_rate_limit.limiter.limit(core_rate_limit.PUBLIC_VIEW)
def read_public_live_session(
    request: Request,
    response: Response,
    token: Annotated[str, Path(min_length=1, max_length=100, description="Share token from the link")],
    db: Annotated[Session, Depends(core_database.get_db)],
    since: Annotated[datetime | None, Query(description="Only points recorded after this time")] = None,
) -> live_tracking_schema.PublicLiveView:
    """Return a live session by its share token.

    Answers 404 for a forged, unknown, ended or expired link, all alike, so this
    unauthenticated endpoint cannot be used to probe sessions.
    """
    response.headers["Cache-Control"] = "no-store"
    return live_tracking_service.get_public_view(token, since, db)
