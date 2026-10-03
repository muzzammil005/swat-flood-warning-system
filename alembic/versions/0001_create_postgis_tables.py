"""Initial schema: enable PostGIS + create all tables from the ORM model manifest.

Revision ID: 0001_initial_create_postgis_and_tables
Revises: (none — first migration)
Create Date: 2026-08-10

Design notes on ordering:

* Native Postgres ENUMs are created *first* because the CREATE TABLE statements
  reference them as column types.
* ``CREATE EXTENSION IF NOT EXISTS postgis`` runs before any table with a
  Geography column (``zones.coordinates``).
* The ``zones`` table carries a self-referential FK
  (``upstream_zone_id REFERENCES zones.id``) — PostgreSQL allows this inside
  a single CREATE TABLE, but for clarity (and compatibility with Alembic auto
  generation) the FK constraint is added as a separate ``ALTER TABLE`` step
  after the table is in place.
* Composite indexes on the three time-series tables (sensor_readings,
  weather_snapshots, risk_assessments) mirror the ``__table_args__`` in
  :mod:`infrastructure.db.models` — ``(zone_id, <timestamp_col>)`` btree,
  which is the exact shape of the "latest N rows for zone Z" queries that the
  append-only repositories run.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography


# Revision identifiers — Alembic convention.
revision = "0001_create_postgis_tables"
down_revision = None
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # 1. PostGIS extension — required before creating any Geography columns.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Native Postgres ENUMs are created implicitly by the inline sa.Enum()
    #    instances inside each create_table() call below via SQLAlchemy's
    #    before_create event dispatch. We deliberately do NOT call .create()
    #    explicitly here because (a) the inline enum creation is automatic,
    #    and (b) explicit + inline creation in the same transaction causes
    #    a "DuplicateObjectError: type already exists" race in Postgres'
    #    transactional DDL because the event dispatch does not pass checkfirst.
    #    Re-running against an already-migrated DB is safe because Alembic's
    #    alembic_version table prevents double execution.

    # 3. Zones (upstream_zone_id FK is added below, after table creation).
    op.create_table(
        "zones",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "coordinates",
            Geography(geometry_type="POINT", srid=4326, spatial_index=True),
            nullable=False,
        ),
        sa.Column("upstream_zone_id", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_foreign_key(
        "fk_zones_upstream_zone_id_zones",
        "zones",
        "zones",
        ["upstream_zone_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 4. ResourceCenters hang off zone via location_zone FK (RESTRICT so a
    # zone with an active centre can't be deleted accidentally).
    op.create_table(
        "resource_centers",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location_zone", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["location_zone"], ["zones.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. Auth tables (Users + API keys).
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "responder", name="user_role", native_enum=True, create_constraint=True),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("owner_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )

    # 6. InventoryItems hang off center_id (CASCADE on delete — removing a
    # centre removes all of its SKUs as a side effect; in practice the
    # ModerateReport/AllocateResources use cases never delete centres).
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("center_id", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["center_id"], ["resource_centers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_inventory_items_center_id", "center_id"),
    )

    # 7. Append-only time-series tables — composite (zone_id, time DESC)
    #    indexes on each.
    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("zone_id", sa.String(length=255), nullable=False),
        sa.Column("water_level_cm", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "real",
                "test",
                name="sensor_source",
                native_enum=True,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_sensor_readings_zone_timestamp", "zone_id", "timestamp"),
    )

    op.create_table(
        "weather_snapshots",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("zone_id", sa.String(length=255), nullable=False),
        sa.Column("rainfall_mm", sa.Float(), nullable=False),
        sa.Column("rainfall_hours", sa.Float(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ttl_seconds", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_weather_snapshots_zone_fetched", "zone_id", "fetched_at"),
    )

    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("zone_id", sa.String(length=255), nullable=False),
        sa.Column(
            "tier",
            sa.Enum(
                "LOW",
                "MEDIUM",
                "HIGH",
                "DANGER",
                name="risk_tier",
                native_enum=True,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_risk_assessments_zone_computed", "zone_id", "computed_at"),
    )

    # 8. Alerts, community reports, manual overrides, audit log.
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("zone_id", sa.String(length=255), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "LOW",
                "MEDIUM",
                "HIGH",
                "DANGER",
                name="alert_severity",
                native_enum=True,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("certainty", sa.String(length=50), nullable=False),
        sa.Column("urgency", sa.String(length=50), nullable=False),
        sa.Column("headline", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "community_reports",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("zone_id", sa.String(length=255), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "Pending",
                "Approved",
                "Rejected",
                name="community_report_status",
                native_enum=True,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "manual_overrides",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("zone_id", sa.String(length=255), nullable=False),
        sa.Column(
            "threat_level",
            sa.Enum(
                "LOW",
                "MEDIUM",
                "HIGH",
                "DANGER",
                name="override_threat_level",
                native_enum=True,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("admin_username", sa.String(length=255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_log_entries",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("actor_username", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_audit_log_entries_actor_timestamp", "actor_username", "timestamp"),
    )


# ---------------------------------------------------------------------------
# Downgrade — reverse order of creation, drop tables then enums then extension.
# In a real deployment DROP EXTENSION postgis is rarely wanted because other
# tables in the same database may depend on it; we keep it for symmetry.
# ---------------------------------------------------------------------------


def downgrade() -> None:
    op.drop_table("audit_log_entries")
    op.drop_table("manual_overrides")
    op.drop_table("community_reports")
    op.drop_table("alerts")

    op.drop_table("risk_assessments")
    op.drop_table("weather_snapshots")
    op.drop_table("sensor_readings")

    op.drop_table("inventory_items")
    op.drop_table("api_keys")
    op.drop_table("users")

    op.drop_table("resource_centers")

    op.drop_constraint("fk_zones_upstream_zone_id_zones", "zones", type_="foreignkey")
    op.drop_table("zones")

    # Drop native enums.
    sa.Enum(name="override_threat_level").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="alert_severity").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="community_report_status").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="sensor_source").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="risk_tier").drop(op.get_bind(), checkfirst=False)

    op.execute("DROP EXTENSION IF EXISTS postgis;")
