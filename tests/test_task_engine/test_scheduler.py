"""Tests for task scheduler."""
from datetime import date
from src.task_engine.scheduler import TaskScheduler


def make_task(action, title, priority, due_date="2024-06-18"):
    return {"action": action, "title": title, "priority": priority,
            "due_date": due_date}


def test_sort_by_priority():
    scheduler = TaskScheduler(today=date(2024, 6, 15))
    tasks = [
        make_task("a", "low task", "low", "2024-08-01"),
        make_task("b", "urgent task", "urgent", "2024-06-18"),
        make_task("c", "high task", "high", "2024-06-20"),
    ]
    ordered = scheduler.sort(tasks)
    assert [t["priority"] for t in ordered] == ["urgent", "high", "low"]


def test_same_priority_sorts_by_due_date():
    scheduler = TaskScheduler(today=date(2024, 6, 15))
    tasks = [
        make_task("a", "later", "high", "2024-07-01"),
        make_task("b", "sooner", "high", "2024-06-16"),
    ]
    ordered = scheduler.sort(tasks)
    assert ordered[0]["title"] == "sooner"


def test_mark_overdue():
    scheduler = TaskScheduler(today=date(2024, 6, 15))
    tasks = [make_task("a", "past due", "high", "2024-06-10")]
    ordered = scheduler.sort(tasks)
    assert ordered[0]["overdue"] is True
