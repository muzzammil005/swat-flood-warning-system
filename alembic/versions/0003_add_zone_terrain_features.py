"""Add zone_terrain_features table with 26 static ML feature columns per zone.

Revision ID: 0003_add_zone_terrain_features
Revises: 0002_add_zone_thresholds
Create Date: 2026-08-16

Design:
* One row per zone, enforced by UNIQUE(zone_id) + ON DELETE CASCADE.
* 26 Float / Integer columns matching the LGBM feature_columns order exactly:
    elevation, slope, stream_proximity, drainage_density, upstream_area, hand,
    landcover_encoded, ndvi, annual_rain_mean,
    rain_jan..rain_dec (12), longitude, latitude,
    rainfall_std, rainfall_max_anomaly, terrain_ruggedness.
* ``landcover_encoded`` stores the LabelEncoder-transformed integer (pre-encoded
  at CSV load time, not the raw landcover code string).
* ``rainfall_std`` / ``rainfall_max_anomaly`` use placeholder formulas until
  Kazim sends 10-year yearly rainfall; re-running the load script overwrites
  them via upsert.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_add_zone_terrain_features"
down_revision = "0002_add_zone_thresholds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "zone_terrain_features",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("zone_id", sa.String(length=255), nullable=False),
        sa.Column("elevation", sa.Float(), nullable=False),
        sa.Column("slope", sa.Float(), nullable=False),
        sa.Column("stream_proximity", sa.Float(), nullable=False),
        sa.Column("drainage_density", sa.Float(), nullable=False),
        sa.Column("upstream_area", sa.Float(), nullable=False),
        sa.Column("hand", sa.Float(), nullable=False),
        sa.Column("landcover_encoded", sa.Integer(), nullable=False),
        sa.Column("ndvi", sa.Float(), nullable=False),
        sa.Column("annual_rain_mean", sa.Float(), nullable=False),
        sa.Column("rain_jan", sa.Float(), nullable=False),
        sa.Column("rain_feb", sa.Float(), nullable=False),
        sa.Column("rain_mar", sa.Float(), nullable=False),
        sa.Column("rain_apr", sa.Float(), nullable=False),
        sa.Column("rain_may", sa.Float(), nullable=False),
        sa.Column("rain_jun", sa.Float(), nullable=False),
        sa.Column("rain_jul", sa.Float(), nullable=False),
        sa.Column("rain_aug", sa.Float(), nullable=False),
        sa.Column("rain_sep", sa.Float(), nullable=False),
        sa.Column("rain_oct", sa.Float(), nullable=False),
        sa.Column("rain_nov", sa.Float(), nullable=False),
        sa.Column("rain_dec", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("rainfall_std", sa.Float(), nullable=False),
        sa.Column("rainfall_max_anomaly", sa.Float(), nullable=False),
        sa.Column("terrain_ruggedness", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("zone_id", name="uq_zone_terrain_features_zone_id"),
    )


def downgrade() -> None:
    op.drop_table("zone_terrain_features")
