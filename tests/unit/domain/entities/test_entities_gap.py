from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.entities import (
    APIKey,
    AuditLogEntry,
    InventoryItem,
    ResourceCenter,
    User,
)
from domain.exceptions import DomainError, InvalidInventoryQuantity

FIXED_TS = datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# ResourceCenter
# ---------------------------------------------------------------------------


class TestResourceCenter:
    def test_valid(self) -> None:
        rc = ResourceCenter(id="rc-1", name="Mingora Fire Station", location_zone="mingora")
        assert rc.name == "Mingora Fire Station"
        assert rc.location_zone == "mingora"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(DomainError):
            ResourceCenter(id="rc-x", name="", location_zone="mingora")

    def test_empty_location_zone_raises(self) -> None:
        with pytest.raises(DomainError):
            ResourceCenter(id="rc-x", name="Depot", location_zone="")


# ---------------------------------------------------------------------------
# InventoryItem
# ---------------------------------------------------------------------------


class TestInventoryItem:
    def test_valid_positive(self) -> None:
        item = InventoryItem(
            id="inv-1", item_name="Sandbag 50kg", quantity=250, center_id="rc-1"
        )
        assert item.quantity == 250

    def test_valid_zero_stock(self) -> None:
        item = InventoryItem(
            id="inv-0", item_name="Rescue boat", quantity=0, center_id="rc-1"
        )
        assert item.quantity == 0

    def test_negative_quantity_raises(self) -> None:
        with pytest.raises(InvalidInventoryQuantity):
            InventoryItem(id="inv-bad", item_name="x", quantity=-1, center_id="rc-1")

    @pytest.mark.parametrize("bad_bool", [True, False])
    def test_bool_not_int_quantity_raises(self, bad_bool: bool) -> None:
        with pytest.raises(InvalidInventoryQuantity):
            InventoryItem(id="inv-bad", item_name="x", quantity=bad_bool, center_id="rc-1")

    def test_float_quantity_raises(self) -> None:
        with pytest.raises(InvalidInventoryQuantity):
            InventoryItem(id="inv-bad", item_name="x", quantity=3.5, center_id="rc-1")  # type: ignore[arg-type]

    def test_empty_item_name_raises(self) -> None:
        with pytest.raises(DomainError):
            InventoryItem(id="i", item_name="", quantity=1, center_id="rc-1")

    def test_empty_center_id_raises(self) -> None:
        with pytest.raises(DomainError):
            InventoryItem(id="i", item_name="x", quantity=1, center_id="")


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class TestUser:
    def test_valid_admin(self) -> None:
        u = User(id="u-1", username="admin_hayat", role="admin", created_at=FIXED_TS)
        assert u.role == "admin"
        assert u.username == "admin_hayat"

    def test_valid_responder(self) -> None:
        u = User(id="u-2", username="responder_khan", role="responder", created_at=FIXED_TS)
        assert u.role == "responder"

    def test_bad_role_raises(self) -> None:
        with pytest.raises(DomainError):
            User(id="u-x", username="x", role="superuser", created_at=FIXED_TS)  # type: ignore[arg-type]

    def test_empty_username_raises(self) -> None:
        with pytest.raises(DomainError):
            User(id="u-x", username="", role="admin", created_at=FIXED_TS)


# ---------------------------------------------------------------------------
# APIKey
# ---------------------------------------------------------------------------


class TestAPIKey:
    def test_valid_active(self) -> None:
        k = APIKey(
            id="k-1",
            key_hash="argon2id$v=19$m=65536,t=3,p=4$...",  # example hash
            owner_name="Field Gauge Logger #7",
            is_active=True,
        )
        assert k.is_active is True

    def test_valid_revoked(self) -> None:
        k = APIKey(id="k-2", key_hash="hashhash", owner_name="Retired box", is_active=False)
        assert k.is_active is False

    def test_empty_key_hash_raises(self) -> None:
        with pytest.raises(DomainError):
            APIKey(id="k-bad", key_hash="", owner_name="x", is_active=True)

    def test_empty_owner_raises(self) -> None:
        with pytest.raises(DomainError):
            APIKey(id="k-bad", key_hash="abc", owner_name="", is_active=True)


# ---------------------------------------------------------------------------
# AuditLogEntry
# ---------------------------------------------------------------------------


class TestAuditLogEntry:
    def test_valid_manual_override_audit(self) -> None:
        entry = AuditLogEntry(
            id="log-1",
            actor_username="admin_hayat",
            action="ManualOverride.issue",
            target="zone:mingora",
            timestamp=FIXED_TS,
        )
        assert entry.action == "ManualOverride.issue"
        assert entry.target == "zone:mingora"

    def test_valid_report_moderation(self) -> None:
        entry = AuditLogEntry(
            id="log-2",
            actor_username="responder_khan",
            action="CommunityReport.approve",
            target="report:cr-42",
            timestamp=FIXED_TS,
        )
        assert entry.actor_username == "responder_khan"

    def test_empty_actor_raises(self) -> None:
        with pytest.raises(DomainError):
            AuditLogEntry(
                id="log-x",
                actor_username="",
                action="x",
                target="x",
                timestamp=FIXED_TS,
            )

    def test_empty_action_raises(self) -> None:
        with pytest.raises(DomainError):
            AuditLogEntry(
                id="log-x",
                actor_username="admin",
                action="",
                target="x",
                timestamp=FIXED_TS,
            )

    def test_empty_target_raises(self) -> None:
        with pytest.raises(DomainError):
            AuditLogEntry(
                id="log-x",
                actor_username="admin",
                action="x",
                target="",
                timestamp=FIXED_TS,
            )
