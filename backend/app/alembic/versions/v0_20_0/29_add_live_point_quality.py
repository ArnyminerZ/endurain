"""29: add position source, signal strength and GPS quality to live points

Revision ID: 5d8e1f3a7c92
Revises: 3b9c5e7a1d24
Create Date: 2026-10-22 00:00:00.000000

A live point can now say where its position came from (the gadget's GPS or the phone's),
how many satellites the fix used and its estimated accuracy, and the phone's mobile signal
as a real measurement in dBm with the kind of measurement it is, instead of the coarse 0-4
level (kept for older clients).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d8e1f3a7c92"
down_revision: str | None = "3b9c5e7a1d24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "live_points",
        sa.Column("phone_signal_dbm", sa.SmallInteger(), nullable=True, comment="Phone mobile signal power in dBm"),
    )
    op.add_column(
        "live_points",
        sa.Column(
            "phone_signal_type",
            sa.String(length=10),
            nullable=True,
            comment="Measurement behind phone_signal_dbm: rsrp, rssi or rscp",
        ),
    )
    op.add_column(
        "live_points",
        sa.Column(
            "position_source",
            sa.String(length=10),
            nullable=True,
            comment="Where the position was measured: gadget or phone",
        ),
    )
    op.add_column(
        "live_points",
        sa.Column("satellites", sa.SmallInteger(), nullable=True, comment="Satellites used for the fix"),
    )
    op.add_column(
        "live_points",
        sa.Column(
            "horizontal_accuracy",
            sa.Float(),
            nullable=True,
            comment="Estimated horizontal accuracy of the fix in meters",
        ),
    )
    op.alter_column(
        "live_points",
        "phone_signal",
        existing_type=sa.SmallInteger(),
        existing_nullable=True,
        comment="Deprecated phone mobile signal level, 0 (none) to 4 (great)",
    )
    op.create_check_constraint(
        "ck_live_points_position_source", "live_points", "position_source IN ('gadget', 'phone')"
    )
    op.create_check_constraint(
        "ck_live_points_phone_signal_type", "live_points", "phone_signal_type IN ('rsrp', 'rssi', 'rscp')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_live_points_phone_signal_type", "live_points", type_="check")
    op.drop_constraint("ck_live_points_position_source", "live_points", type_="check")
    op.alter_column(
        "live_points",
        "phone_signal",
        existing_type=sa.SmallInteger(),
        existing_nullable=True,
        comment="Phone mobile signal level, 0 (none) to 4 (great)",
    )
    op.drop_column("live_points", "horizontal_accuracy")
    op.drop_column("live_points", "satellites")
    op.drop_column("live_points", "position_source")
    op.drop_column("live_points", "phone_signal_type")
    op.drop_column("live_points", "phone_signal_dbm")
