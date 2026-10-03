"""Integration test for FCMStubNotifier."""

from __future__ import annotations

import logging
from datetime import datetime

import pytest
from domain.entities.alert import Alert
from infrastructure.notifications import FCMStubNotifier


@pytest.mark.asyncio
async def test_fcm_stub_notifier(caplog: pytest.LogCaptureFixture) -> None:
    """Test that FCMStubNotifier logs alerts without raising."""
    # Set log level to capture INFO logs
    caplog.set_level(logging.INFO)
    
    notifier = FCMStubNotifier()
    
    # Create a test alert
    alert = Alert(
        zone_id="test-zone-1",
        severity="HIGH",
        certainty="Observed",
        urgency="Immediate",
        headline="Test Flood Alert",
        description="Water level rising rapidly in test zone",
        sent_at=datetime.now(),
    )
    
    # Clear any existing logs
    caplog.clear()
    
    # Should log when sending to recipients
    await notifier.send_alert(alert, recipients=["recipient1", "recipient2"])
    
    # Check that it logged the alert
    # The log message contains "FCMStubNotifier would send HIGH‑severity alert"
    # Note: record.message only contains the first line, record.getMessage() has full message
    assert any("FCMStubNotifier would send" in record.getMessage() for record in caplog.records)
    assert any("Zone test-zone-1 — HIGH ALERT" in record.getMessage() for record in caplog.records)
    assert any("Test Flood Alert" in record.getMessage() for record in caplog.records)
    
    caplog.clear()
    
    # Should handle empty recipients gracefully (logs but doesn't send)
    await notifier.send_alert(alert, recipients=[])
    
    # Check that it logged skipping due to no recipients
    assert any("has no recipients, skipping" in record.getMessage() for record in caplog.records)
    
    caplog.clear()
    
    # Should handle multiple recipients
    await notifier.send_alert(
        alert,
        recipients=["user1", "user2", "user3", "user4", "user5"]
    )
    
    # Check that it logged with correct recipient count
    assert any("5 recipient" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_fcm_stub_different_severity_levels(caplog: pytest.LogCaptureFixture) -> None:
    """Test that different severity levels are logged appropriately."""
    # Set log level to capture INFO logs
    caplog.set_level(logging.INFO)
    
    notifier = FCMStubNotifier()
    
    severities = ["LOW", "MEDIUM", "HIGH", "DANGER"]
    
    for severity in severities:
        caplog.clear()
        
        alert = Alert(
            zone_id=f"zone-{severity.lower()}",
            severity=severity,
            certainty="Likely",
            urgency="Expected",
            headline=f"{severity} severity test",
            description=f"Testing {severity} severity level",
            sent_at=datetime.now(),
        )
        
        # Should not raise
        await notifier.send_alert(alert, recipients=["test-recipient"])
        
        # Check that it logged with correct severity
        # The actual log message starts with "FCMStubNotifier would send"
        assert any("FCMStubNotifier would send" in record.getMessage() for record in caplog.records)
        assert any(f"{severity.upper()} ALERT" in record.message for record in caplog.records)