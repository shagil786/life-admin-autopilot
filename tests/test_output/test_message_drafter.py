"""Tests for message drafter."""
from src.output.message_drafter import MessageDrafter


def test_draft_cancel_message():
    drafter = MessageDrafter()
    msg = drafter.draft_cancellation(
        {"name": "Netflix", "amount": 15.99, "billing_cycle": "monthly"}
    )
    assert "Netflix" in msg
    assert "cancel" in msg.lower()
    assert "15.99" in msg


def test_draft_return_message():
    drafter = MessageDrafter()
    msg = drafter.draft_return(
        {"vendor": "Amazon", "amount": 49.99, "date": "2024-05-21"}
    )
    assert "Amazon" in msg
    assert "return" in msg.lower()
    assert "49.99" in msg


def test_draft_has_placeholder_for_order_id():
    drafter = MessageDrafter()
    msg = drafter.draft_return(
        {"vendor": "Amazon", "amount": 49.99, "date": "2024-05-21"}
    )
    assert "[ORDER ID]" in msg


def test_handles_missing_fields():
    drafter = MessageDrafter()
    msg = drafter.draft_cancellation({"name": "Netflix"})
    assert "Netflix" in msg
    assert "cancel" in msg.lower()
