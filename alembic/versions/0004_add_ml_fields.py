"""Add ML fields to RiskAssessment table.

Revision ID: 0004_add_ml_fields
Revises: 0003_add_zone_terrain_features
Create Date: 2026-08-24

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_add_ml_fields"
down_revision = "0003_add_zone_terrain_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('risk_assessments', sa.Column('combined_rain_mm', sa.Float(), nullable=True))
    op.add_column('risk_assessments', sa.Column('expected_rain_mm', sa.Float(), nullable=True))
    op.add_column('risk_assessments', sa.Column('rainfall_anomaly_ratio', sa.Float(), nullable=True))
    op.add_column('risk_assessments', sa.Column('top_contributing_features', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('risk_assessments', 'top_contributing_features')
    op.drop_column('risk_assessments', 'rainfall_anomaly_ratio')
    op.drop_column('risk_assessments', 'expected_rain_mm')
    op.drop_column('risk_assessments', 'combined_rain_mm')
