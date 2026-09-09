"""Strands tools wrapping the life-admin pipeline for the agent."""
from datetime import date

from strands import tool

from src.main import Pipeline
from src.output.message_drafter import MessageDrafter
from src.task_engine.rules import RuleEngine
from src.task_engine.scheduler import TaskScheduler

# Module-level state so tools share one pipeline instance.
_pipeline: Pipeline = None
_drafter = MessageDrafter()


def _get_pipeline() -> Pipeline:
    global _pipeline
    if _pipeline is None:
        today = date.today()
        _pipeline = Pipeline(
            rules=RuleEngine(today=today),
            scheduler=TaskScheduler(today=today),
        )
    return _pipeline


@tool(
    description=(
        "Scan a folder of life-admin documents (receipts, subscriptions, "
        "warranties as .txt/.md/.pdf) and return a prioritized action list. "
        "Use path 'data/samples' for the demo folder."
    )
)
def scan_documents(path: str = "data/samples") -> str:
    """Ingest -> extract -> evaluate -> format. Returns the action list."""
    pipeline = _get_pipeline()
    import glob
    from pathlib import Path

    target = Path(path)
    if target.is_dir():
        files = [
            str(p)
            for p in sorted(target.iterdir())
            if p.suffix.lower() in (".pdf", ".txt", ".md", ".eml")
        ]
    elif target.is_file():
        files = [str(target)]
    else:
        return f"Error: path not found: {path}"

    result = pipeline.run(files)
    return result["formatted"] + f"\n\n{result['summary']}"


@tool(
    description=(
        "Draft a ready-to-send message for a task: a subscription cancellation "
        "email or a vendor return request. Provide the task action "
        "('cancel_or_review' or 'return_or_exchange') and key details "
        "(name/vendor, amount, date)."
    )
)
def draft_action_message(
    action: str, name: str, amount: float = 0.0, date_str: str = ""
) -> str:
    """Draft a cancel/return message with placeholders. No message is sent."""
    if action == "cancel_or_review":
        return _drafter.draft_cancellation(
            {"name": name, "amount": amount, "billing_cycle": "month"}
        )
    if action == "return_or_exchange":
        return _drafter.draft_return(
            {"vendor": name, "amount": amount, "date": date_str or None}
        )
    return f"Unknown action '{action}'. Use cancel_or_review or return_or_exchange."


@tool(
    description=(
        "Get today's date, for reasoning about return windows, renewal "
        "deadlines, and warranty expiry."
    )
)
def get_today() -> str:
    return date.today().isoformat()
