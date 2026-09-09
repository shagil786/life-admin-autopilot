"""Tests for task engine rules."""
from datetime import date, timedelta
from src.task_engine.rules import RuleEngine


def make_engine(today=None):
    return RuleEngine(today=today or date(2024, 6, 15))


def test_return_window_urgent():
    engine = make_engine()
    tasks = engine.evaluate_receipt(
        {"vendor": "Amazon", "amount": 49.99, "date": "2024-05-21"}
    )
    assert len(tasks) == 1
    task = tasks[0]
    assert task["action"] == "return_or_exchange"
    assert task["priority"] == "urgent"  # 25 days elapsed, 5 days left in window


def test_return_window_not_urgent():
    engine = make_engine()
    tasks = engine.evaluate_receipt(
        {"vendor": "Amazon", "amount": 49.99, "date": "2024-06-14"}
    )
    assert tasks[0]["priority"] == "low"


def test_no_task_without_date():
    engine = make_engine()
    assert engine.evaluate_receipt({"vendor": "Amazon", "amount": 10.0}) == []


def test_subscription_cancel_deadline():
    engine = make_engine()
    tasks = engine.evaluate_subscription(
        {"name": "Netflix", "amount": 15.99, "billing_cycle": "monthly",
         "next_billing_date": "2024-06-18"}
    )
    assert len(tasks) == 1
    assert tasks[0]["action"] == "cancel_or_review"
    assert tasks[0]["priority"] == "urgent"  # 3 days before renewal
    assert "Netflix" in tasks[0]["title"]


def test_subscription_far_away_not_urgent():
    engine = make_engine()
    tasks = engine.evaluate_subscription(
        {"name": "Netflix", "amount": 15.99, "billing_cycle": "monthly",
         "next_billing_date": "2024-07-15"}
    )
    assert tasks[0]["priority"] == "low"


def test_warranty_expiry():
    engine = make_engine()
    tasks = engine.evaluate_warranty(
        {"product": "Sony WH-1000XM5", "warranty_years": 2,
         "purchase_date": "2022-06-01", "warranty_expires": "2024-06-20"}
    )
    assert len(tasks) == 1
    assert tasks[0]["action"] == "check_warranty"
    assert tasks[0]["priority"] == "urgent"
