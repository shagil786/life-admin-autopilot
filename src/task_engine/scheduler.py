"""Task scheduler: sorts tasks by priority and due date."""
from datetime import date

PRIORITY_ORDER = {"overdue": 0, "urgent": 1, "high": 2, "medium": 3, "low": 4}


class TaskScheduler:
    def __init__(self, today: date):
        self.today = today

    def sort(self, tasks: list) -> list:
        annotated = []
        for task in tasks:
            task = dict(task)
            if task.get("due_date"):
                due = date.fromisoformat(task["due_date"])
                if due < self.today and task.get("priority") != "overdue":
                    task["overdue"] = True
                else:
                    task["overdue"] = False
            else:
                task["overdue"] = False
            annotated.append(task)

        annotated.sort(key=self._sort_key)
        return annotated

    def _sort_key(self, task: dict):
        priority_rank = PRIORITY_ORDER.get(task.get("priority", "low"), 99)
        due = task.get("due_date") or "9999-12-31"
        return (priority_rank, due)
