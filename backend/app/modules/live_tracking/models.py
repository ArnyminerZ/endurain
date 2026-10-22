"""SQLAlchemy ORM models for live tracking."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

import modules.live_tracking.constants as live_tracking_constants
from core.database import Base, TimestampMixin


class LiveSession(Base, TimestampMixin):
    """One live tracking session.

    Attributes:
        id: UUID string; also the identity inside the share token.
        user_id: Owner of the session.
        status: ``active`` or ``ended``.
        activity_type: Activity type name handed to the GPX parser on stop.
        name: Optional display name of the workout.
        started_at: When the session started.
        last_update_at: When the last point was received (start time if none).
        expires_at: Hard end of the session, whatever the client does.
        ended_at: When the session stopped, if it has.
    """

    __tablename__ = "live_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'ended')", name="ck_live_sessions_status"),
        Index(
            "uq_live_sessions_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(length=36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Session UUID, also embedded in the share token",
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the user who owns the session",
    )
    status: Mapped[str] = mapped_column(
        String(length=20),
        nullable=False,
        default=live_tracking_constants.SessionStatus.ACTIVE.value,
        server_default=live_tracking_constants.SessionStatus.ACTIVE.value,
        comment="Session status: active or ended",
    )
    activity_type: Mapped[str] = mapped_column(
        String(length=50),
        nullable=False,
        default=live_tracking_constants.DEFAULT_ACTIVITY_TYPE,
        comment="Activity type name shown to viewers",
    )
    name: Mapped[str | None] = mapped_column(
        String(length=150),
        nullable=True,
        comment="Optional display name of the workout",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the session started",
    )
    last_update_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the last point was received",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Hard deadline after which the session is ended server-side",
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the session ended",
    )


class LivePoint(Base):
    """One position update of a live session.

    Attributes:
        id: Surrogate primary key.
        session_id: The session the point belongs to.
        recorded_at: When the device recorded the point.
        latitude: Latitude in degrees.
        longitude: Longitude in degrees.
        elevation: Elevation in meters.
        speed: Speed in meters per second.
        heart_rate: Heart rate in bpm.
        cadence: Cadence in rpm/spm.
        temperature: Ambient temperature in degrees Celsius.
        skin_temperature: Skin temperature in degrees Celsius.
    """

    __tablename__ = "live_points"
    __table_args__ = (UniqueConstraint("session_id", "recorded_at", name="uq_live_points_session_recorded_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("live_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the live session the point belongs to",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the device recorded the point",
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False, comment="Latitude in degrees")
    longitude: Mapped[float] = mapped_column(Float, nullable=False, comment="Longitude in degrees")
    elevation: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Elevation in meters")
    speed: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Speed in meters per second")
    heart_rate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="Heart rate in bpm")
    cadence: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="Cadence")
    temperature: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Ambient temperature in degrees Celsius"
    )
    skin_temperature: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Skin temperature in degrees Celsius"
    )


class LiveContact(Base, TimestampMixin):
    """A person the user wants notified when a live session starts.

    Attributes:
        id: Surrogate primary key.
        user_id: The user whose contact this is.
        name: Display name of the contact.
        email: Email address the start notification is sent to.
    """

    __tablename__ = "live_contacts"
    __table_args__ = (UniqueConstraint("user_id", "email", name="uq_live_contacts_user_email"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the user who owns the contact",
    )
    name: Mapped[str] = mapped_column(String(length=100), nullable=False, comment="Display name of the contact")
    email: Mapped[str] = mapped_column(String(length=255), nullable=False, comment="Contact email address")
