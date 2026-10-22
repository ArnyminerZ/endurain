"""Pydantic schemas for live tracking."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictInt, field_validator, model_validator

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
        temperature: Ambient temperature in degrees Celsius.
        skin_temperature: Skin temperature in degrees Celsius.
        gadget_battery: Battery of the recording gadget (e.g. the watch), in percent.
        phone_battery: Battery of the phone relaying the data, in percent.
        phone_signal: Deprecated coarse phone signal level, 0 (none) to 4 (great). Send
            ``phone_signal_dbm`` and ``phone_signal_type`` instead.
        phone_signal_dbm: Phone mobile signal power in dBm (e.g. -95).
        phone_signal_type: Which measurement ``phone_signal_dbm`` is: ``rsrp`` (LTE/5G),
            ``rssi`` or ``rscp`` (3G). Required with ``phone_signal_dbm``.
        position_source: Where the position was measured: ``gadget`` (the watch's GPS) or
            ``phone``.
        satellites: Satellites used for the fix, when known.
        horizontal_accuracy: Estimated horizontal accuracy of the fix, in meters.
    """

    model_config = ConfigDict(extra="forbid")

    recorded_at: datetime
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    elevation: float | None = Field(default=None, ge=-1000, le=10000)
    speed: float | None = Field(default=None, ge=0, le=200)
    heart_rate: int | None = Field(default=None, ge=0, le=300)
    cadence: int | None = Field(default=None, ge=0, le=300)
    temperature: float | None = Field(default=None, ge=-90, le=80)
    skin_temperature: float | None = Field(default=None, ge=-20, le=60)
    gadget_battery: int | None = Field(default=None, ge=0, le=100)
    phone_battery: int | None = Field(default=None, ge=0, le=100)
    phone_signal: int | None = Field(default=None, ge=0, le=4)
    phone_signal_dbm: int | None = Field(
        default=None, ge=live_tracking_constants.MIN_SIGNAL_DBM, le=live_tracking_constants.MAX_SIGNAL_DBM
    )
    phone_signal_type: live_tracking_constants.SignalType | None = None
    position_source: live_tracking_constants.PositionSource | None = None
    satellites: int | None = Field(default=None, ge=0, le=live_tracking_constants.MAX_SATELLITES)
    horizontal_accuracy: float | None = Field(default=None, ge=0, le=live_tracking_constants.MAX_HORIZONTAL_ACCURACY_M)

    @model_validator(mode="after")
    def _signal_has_a_type(self) -> "LivePointIn":
        """Require the measurement type with a dBm reading, and the reading with a type.

        Returns:
            The validated point.

        Raises:
            ValueError: If only one of ``phone_signal_dbm`` and ``phone_signal_type`` is set.
        """
        if (self.phone_signal_dbm is None) != (self.phone_signal_type is None):
            raise ValueError("phone_signal_dbm and phone_signal_type must be sent together")
        return self


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
    temperature: float | None = None
    skin_temperature: float | None = None
    gadget_battery: int | None = None
    phone_battery: int | None = None
    phone_signal: int | None = None
    phone_signal_dbm: int | None = None
    phone_signal_type: live_tracking_constants.SignalType | None = None
    position_source: live_tracking_constants.PositionSource | None = None
    satellites: int | None = None
    horizontal_accuracy: float | None = None

    _utc = field_validator("recorded_at")(_as_utc)


class LiveSessionStart(BaseModel):
    """The body that starts a live session.

    Attributes:
        activity_type: Activity type label shown to viewers (e.g. ``Run``).
        name: Optional display name of the workout.
        notify_contact_ids: Contacts to email; ``None`` means every contact.
        update_interval_seconds: How often the client expects to push points. Viewers
            use it to decide when to warn that updates stopped arriving.
    """

    model_config = ConfigDict(extra="forbid")

    activity_type: str = Field(default=live_tracking_constants.DEFAULT_ACTIVITY_TYPE, min_length=1, max_length=50)
    name: str | None = Field(default=None, max_length=150)
    notify_contact_ids: list[StrictInt] | None = Field(default=None, max_length=100)
    update_interval_seconds: int = Field(
        default=live_tracking_constants.DEFAULT_UPDATE_INTERVAL_SECONDS,
        ge=live_tracking_constants.MIN_UPDATE_INTERVAL_SECONDS,
        le=live_tracking_constants.MAX_UPDATE_INTERVAL_SECONDS,
    )


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
    update_interval_seconds: int
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
        update_interval_seconds: How often the client said it would push points.
        latest: The newest point, if any.
        points: The track (only points after ``since`` when it was given).
        total_points: Points stored for the session.
    """

    athlete: str
    activity_type: str
    name: str | None = None
    started_at: datetime
    last_update_at: datetime
    update_interval_seconds: int
    latest: LivePointRead | None = None
    points: list[LivePointRead]
    total_points: int
