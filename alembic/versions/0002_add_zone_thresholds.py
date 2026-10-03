"""Add zone_thresholds table with one-row-per-zone unique invariant.

Revision ID: 0002_add_zone_thresholds
Revises: 0001_create_postgis_tables
Create Date: 2026-08-10

Design:

* ``zone_thresholds`` carries per-zone calibration knobs (water warning level,
  water critical level, heavy rain threshold) as a *separate* aggregate from
  the ``zones`` table itself. This lets admins re-calibrate thresholds
  independently of renaming a zone or editing the river-graph edges, and the
  ``UNIQUE(zone_id)`` constraint enforces exactly-one-row-per-zone semantics
  in the database rather than by application convention.
* ``ON DELETE CASCADE`` on ``zone_id`` — deleting a zone deletes its
  thresholds too (orphan thresholds are meaningless).
* No new ENUMs or PostGIS types needed here — all columns are primitives.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_add_zone_thresholds"
down_revision = "0001_create_postgis_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "zone_thresholds",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("zone_id", sa.String(length=255), nullable=False),
        sa.Column("water_warning_level_cm", sa.Float(), nullable=False),
        sa.Column("water_critical_level_cm", sa.Float(), nullable=False),
        sa.Column("heavy_rain_threshold_mm", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["zone_id"], ["zones.id"], ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("zone_id", name="uq_zone_thresholds_zone_id"),
    )


def downgrade() -> None:
    op.drop_table("zone_thresholds")
