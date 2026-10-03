"""update_multiclass_xgboost_features

Revision ID: 723fa57f47f9
Revises: 0004_add_ml_fields
Create Date: 2026-10-03 14:05:01.884615

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '723fa57f47f9'
down_revision: Union[str, None] = '0004_add_ml_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('zone_terrain_features', 'annual_rain_mean')
    op.drop_column('zone_terrain_features', 'terrain_ruggedness')
    op.drop_column('zone_terrain_features', 'rainfall_std')
    op.drop_column('zone_terrain_features', 'rainfall_max_anomaly')


def downgrade() -> None:
    op.add_column('zone_terrain_features', sa.Column('rainfall_max_anomaly', sa.Float(), nullable=False))
    op.add_column('zone_terrain_features', sa.Column('rainfall_std', sa.Float(), nullable=False))
    op.add_column('zone_terrain_features', sa.Column('terrain_ruggedness', sa.Float(), nullable=False))
    op.add_column('zone_terrain_features', sa.Column('annual_rain_mean', sa.Float(), nullable=False))
