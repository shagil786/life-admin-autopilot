"""Tests for task formatter."""
from src.output.task_formatter import format_tasks, format_summary


TASKS = [
    {
        "action": "cancel_or_review",
        "title": "Netflix renews on 2024-06-18 ($15.99/month) — cancel if unused",
        "priority": "urgent",
        "due_date": "2024-06-18",
        "overdue": False,
    },
    {
        "action": "return_or_exchange",
        "title": "Return window for Amazon ($49.99) closes 2024-06-20",
        "priority": "high",
        "due_date": "2024-06-20",
        "overdue": False,
    },
]


def test_format_tasks_includes_titles():
    out = format_tasks(TASKS)
    assert "Netflix" in out
    assert "Amazon" in out
    assert "URGENT" in out.upper()


def test_format_tasks_empty():
    out = format_tasks([])
    assert "no tasks" in out.lower()


def test_format_tasks_marks_overdue():
    tasks = [dict(TASKS[0], overdue=True)]
    out = format_tasks(tasks)
    assert "OVERDUE" in out.upper()


def test_format_summary_counts():
    out = format_summary(TASKS)
    assert "2" in out
    assert "1 urgent" in out.lower()
