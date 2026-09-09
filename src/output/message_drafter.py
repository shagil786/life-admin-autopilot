"""Drafts natural-language action messages for tasks."""
from src.extraction.base import BaseExtractor  # noqa: F401 (shared interface pattern)


class MessageDrafter:
    """Drafts return/cancellation messages with placeholders for user edits."""

    def draft_cancellation(self, sub: dict) -> str:
        name = sub.get("name") or "my subscription"
        amount = sub.get("amount")
        cycle = sub.get("billing_cycle") or "billing period"
        price = f"${amount}/{cycle}" if amount else "the current rate"
        return (
            f"Hello,\n\n"
            f"I would like to cancel my {name} subscription, which is billed at "
            f"{price}. Please cancel it effective at the end of the current "
            f"billing period and confirm by reply.\n\n"
            f"Account email: [ACCOUNT EMAIL]\n"
            f"Thank you,\n[YOUR NAME]"
        )

    def draft_return(self, receipt: dict) -> str:
        vendor = receipt.get("vendor") or "the store"
        amount = receipt.get("amount")
        date = receipt.get("date") or "[PURCHASE DATE]"
        price = f"${amount}" if amount else "[AMOUNT]"
        return (
            f"Hello {vendor} support,\n\n"
            f"I purchased an item on {date} (order [ORDER ID], {price}) that I "
            f"would like to return for a refund. The item is unopened/unused "
            f"and within the return window.\n\n"
            f"Please send return instructions and a prepaid label if "
            f"available.\n\n"
            f"Thank you,\n[YOUR NAME]"
        )
