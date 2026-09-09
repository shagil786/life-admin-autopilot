"""Formats task lists for CLI display."""
from src.task_engine.scheduler import PRIORITY_ORDER

PRIORITY_BADGES = {
    "overdue": "!! OVERDUE",
    "urgent": "URGENT",
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "low",
}


def format_tasks(tasks: list) -> str:
    """Render a prioritized task list for the terminal."""
    if not tasks:
        return "No tasks found — you're all caught up! 🎉"

    lines = ["=" * 60, "LIFE ADMIN — ACTION LIST", "=" * 60]
    for i, task in enumerate(tasks, 1):
        badge = PRIORITY_BADGES.get(task.get("priority", "low"), "low")
        if task.get("overdue"):
            badge = PRIORITY_BADGES["overdue"]
        due = task.get("due_date") or "—"
        lines.append(
            f"\n{i}. [{badge}] {task['title']}"
            f"\n   action: {task.get('action', '?')}   due: {due}"
        )
    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def format_summary(tasks: list) -> str:
    """One-line summary of task counts by priority."""
    if not tasks:
        return "No tasks found — you're all caught up! 🎉"
    counts = {}
    for task in tasks:
        p = "overdue" if task.get("overdue") else task.get("priority", "low")
        counts[p] = counts.get(p, 0) + 1
    parts = [f"{n} {label}" for label, n in
             sorted(counts.items(), key=lambda kv: PRIORITY_ORDER.get(kv[0], 99))]
    return f"{len(tasks)} tasks: " + ", ".join(parts)
