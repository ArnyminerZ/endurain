"""28: add live tracking

Revision ID: 3b9c5e7a1d24
Revises: d54bdd779392
Create Date: 2026-10-22 00:00:00.000000

Backs real-time position sharing. ``live_sessions`` is one recording that viewers
can follow through a share link, ``live_points`` holds the positions pushed while
it is live (deleted once the session becomes an activity), and ``live_contacts``
is the per-user list of people emailed when a session starts.

The share link is derived from the session id and the server secret, so no token
is stored. The partial unique index allows one active session per user.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3b9c5e7a1d24"
down_revision: str | None = "d54bdd779392"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "live_sessions",
        sa.Column("id", sa.String(length=36), nullable=False, comment="Session UUID, also embedded in the share token"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="ID of the user who owns the session"),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
            comment="Session status: active or ended",
        ),
        sa.Column(
            "activity_type",
            sa.String(length=50),
            nullable=False,
            comment="Activity type name used when the session becomes an activity",
        ),
        sa.Column("name", sa.String(length=150), nullable=True, comment="Optional display name of the workout"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, comment="When the session started"),
        sa.Column(
            "last_update_at", sa.DateTime(timezone=True), nullable=False, comment="When the last point was received"
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Hard deadline after which the session is ended server-side",
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True, comment="When the session ended"),
        *_timestamps(),
        sa.CheckConstraint("status IN ('active', 'ended')", name="ck_live_sessions_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_live_sessions_user_id"), "live_sessions", ["user_id"], unique=False)
    op.create_index(
        "uq_live_sessions_one_active_per_user",
        "live_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "live_points",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "session_id", sa.String(length=36), nullable=False, comment="ID of the live session the point belongs to"
        ),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), nullable=False, comment="When the device recorded the point"
        ),
        sa.Column("latitude", sa.Float(), nullable=False, comment="Latitude in degrees"),
        sa.Column("longitude", sa.Float(), nullable=False, comment="Longitude in degrees"),
        sa.Column("elevation", sa.Float(), nullable=True, comment="Elevation in meters"),
        sa.Column("speed", sa.Float(), nullable=True, comment="Speed in meters per second"),
        sa.Column("heart_rate", sa.SmallInteger(), nullable=True, comment="Heart rate in bpm"),
        sa.Column("cadence", sa.SmallInteger(), nullable=True, comment="Cadence"),
        sa.Column("temperature", sa.Float(), nullable=True, comment="Ambient temperature in degrees Celsius"),
        sa.Column("skin_temperature", sa.Float(), nullable=True, comment="Skin temperature in degrees Celsius"),
        sa.ForeignKeyConstraint(["session_id"], ["live_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "recorded_at", name="uq_live_points_session_recorded_at"),
    )
    op.create_index(op.f("ix_live_points_session_id"), "live_points", ["session_id"], unique=False)

    op.create_table(
        "live_contacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="ID of the user who owns the contact"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="Display name of the contact"),
        sa.Column("email", sa.String(length=255), nullable=False, comment="Contact email address"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "email", name="uq_live_contacts_user_email"),
    )
    op.create_index(op.f("ix_live_contacts_id"), "live_contacts", ["id"], unique=False)
    op.create_index(op.f("ix_live_contacts_user_id"), "live_contacts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_live_contacts_user_id"), table_name="live_contacts")
    op.drop_index(op.f("ix_live_contacts_id"), table_name="live_contacts")
    op.drop_table("live_contacts")
    op.drop_index(op.f("ix_live_points_session_id"), table_name="live_points")
    op.drop_table("live_points")
    op.drop_index("uq_live_sessions_one_active_per_user", table_name="live_sessions")
    op.drop_index(op.f("ix_live_sessions_user_id"), table_name="live_sessions")
    op.drop_table("live_sessions")
