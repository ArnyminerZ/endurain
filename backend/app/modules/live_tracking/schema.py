"""Pydantic schemas for live tracking."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictInt, field_validator

import modules.live_tracking.constants as live_tracking_constants


def _as_utc(value: datetime | None) -> datetime | None:
    """Treat a naive datetime read back from the database as UTC.

    Args:
        value: The datetime, or ``None``.

    Returns:
        The same instant with a timezone, or ``None``.
    """
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class LivePointIn(BaseModel):
    """One position update pushed by the client.

    Attributes:
        recorded_at: When the device recorded the point (timezone-aware).
        latitude: Latitude in degrees.
        longitude: Longitude in degrees.
        elevation: Elevation in meters.
        speed: Speed in meters per second.
        heart_rate: Heart rate in bpm.
        cadence: Cadence.
    """

    model_config = ConfigDict(extra="forbid")

    recorded_at: datetime
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    elevation: float | None = Field(default=None, ge=-1000, le=10000)
    speed: float | None = Field(default=None, ge=0, le=200)
    heart_rate: int | None = Field(default=None, ge=0, le=300)
    cadence: int | None = Field(default=None, ge=0, le=300)


class LivePointsPush(BaseModel):
    """A batch of points pushed in one request.

    Attributes:
        points: The points; resending one already stored is harmless.
    """

    model_config = ConfigDict(extra="forbid")

    points: list[LivePointIn] = Field(..., min_length=1, max_length=live_tracking_constants.MAX_POINTS_PER_PUSH)


class LivePointRead(BaseModel):
    """A stored point as returned to clients."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    recorded_at: datetime
    latitude: float
    longitude: float
    elevation: float | None = None
    speed: float | None = None
    heart_rate: int | None = None
    cadence: int | None = None

    _utc = field_validator("recorded_at")(_as_utc)


class LiveSessionStart(BaseModel):
    """The body that starts a live session.

    Attributes:
        activity_type: Activity type name (e.g. ``Run``); unknown names become ``Workout``.
        name: Optional display name of the workout.
        notify_contact_ids: Contacts to email; ``None`` means every contact.
    """

    model_config = ConfigDict(extra="forbid")

    activity_type: str = Field(default=live_tracking_constants.DEFAULT_ACTIVITY_TYPE, min_length=1, max_length=50)
    name: str | None = Field(default=None, max_length=150)
    notify_contact_ids: list[StrictInt] | None = Field(default=None, max_length=100)


class LiveSessionRead(BaseModel):
    """A live session as the owner sees it."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    user_id: int
    status: live_tracking_constants.SessionStatus
    activity_type: str
    name: str | None = None
    started_at: datetime
    last_update_at: datetime
    expires_at: datetime
    ended_at: datetime | None = None

    _utc = field_validator("started_at", "last_update_at", "expires_at", "ended_at")(_as_utc)


class LiveSessionStarted(BaseModel):
    """The response to starting a session.

    Attributes:
        session: The created session.
        share_url: The public link to hand out.
        notified_contacts: How many contacts an email was queued for.
        email_enabled: Whether the server can send email at all.
    """

    session: LiveSessionRead
    share_url: str
    notified_contacts: int
    email_enabled: bool


class LiveSessionOwnerView(BaseModel):
    """The owner's view of a session: the session, its link and its points."""

    session: LiveSessionRead
    share_url: str
    points: list[LivePointRead]


class LivePushResult(BaseModel):
    """The response to a push.

    Attributes:
        accepted: Points stored by this request (duplicates are not counted).
        total_points: Points stored for the session.
    """

    accepted: int
    total_points: int


class LiveSessionStopped(BaseModel):
    """The response to stopping a session.

    Attributes:
        session: The ended session.
        activity_ids: Ids of the activities created from the session.
        discarded: True when there were too few points to make an activity.
    """

    session: LiveSessionRead
    activity_ids: list[int]
    discarded: bool


class LiveContactCreate(BaseModel):
    """The body that adds a contact."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr


class LiveContactRead(BaseModel):
    """A contact as returned to the owner."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    name: str
    email: str


class PublicLiveView(BaseModel):
    """What an anonymous viewer of the share link sees.

    Attributes:
        athlete: First name of the athlete.
        activity_type: Activity type name.
        name: Display name of the workout.
        started_at: When the session started.
        last_update_at: When the last point arrived.
        latest: The newest point, if any.
        points: The track (only points after ``since`` when it was given).
        total_points: Points stored for the session.
    """

    athlete: str
    activity_type: str
    name: str | None = None
    started_at: datetime
    last_update_at: datetime
    latest: LivePointRead | None = None
    points: list[LivePointRead]
    total_points: int
