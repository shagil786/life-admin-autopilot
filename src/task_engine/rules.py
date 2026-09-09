"""Rule engine: turns extracted data into prioritized tasks.

Rules (from spec):
- Return window: 30 days from purchase -> return/exchange task, urgent when <= 7 days left
- Subscription renewal: cancel/review task, urgent when <= 7 days before next bill
- Warranty expiry: check-warranty task, urgent when <= 30 days to expiry
"""
from dataclasses import dataclass
from datetime import date

RETURN_WINDOW_DAYS = 30
URGENT_RETURN_DAYS = 7
URGENT_SUBSCRIPTION_DAYS = 7
URGENT_WARRANTY_DAYS = 30


@dataclass
class RuleEngine:
    today: date

    def _days_until(self, iso_date: str) -> int:
        target = date.fromisoformat(iso_date)
        return (target - self.today).days

    def _priority_for_days_left(self, days_left: int, urgent_threshold: int) -> str:
        if days_left <= 0:
            return "overdue"
        if days_left <= urgent_threshold:
            return "urgent"
        if days_left <= urgent_threshold * 3:
            return "high"
        return "low"

    def evaluate_receipt(self, receipt: dict) -> list:
        """Return window rule: returns allowed within 30 days of purchase."""
        if not receipt.get("date"):
            return []
        purchase = date.fromisoformat(receipt["date"])
        days_elapsed = (self.today - purchase).days
        if days_elapsed < 0 or days_elapsed > RETURN_WINDOW_DAYS:
            return []
        days_left = RETURN_WINDOW_DAYS - days_elapsed
        priority = self._priority_for_days_left(days_left, URGENT_RETURN_DAYS)
        due = date.fromordinal(purchase.toordinal() + RETURN_WINDOW_DAYS)
        return [{
            "action": "return_or_exchange",
            "title": f"Return window for {receipt.get('vendor', 'purchase')} "
                     f"(${receipt.get('amount', '?')}) closes {due.isoformat()}",
            "priority": priority,
            "due_date": due.isoformat(),
            "details": receipt,
        }]

    def evaluate_subscription(self, sub: dict) -> list:
        """Renewal rule: review/cancel before the next billing date."""
        if not sub.get("next_billing_date"):
            return []
        days_left = self._days_until(sub["next_billing_date"])
        if days_left > 60:
            return []
        priority = self._priority_for_days_left(days_left, URGENT_SUBSCRIPTION_DAYS)
        name = sub.get("name") or "subscription"
        return [{
            "action": "cancel_or_review",
            "title": f"{name} renews on {sub['next_billing_date']} "
                     f"(${sub.get('amount', '?')}/{sub.get('billing_cycle', '?')}) "
                     f"— cancel if unused",
            "priority": priority,
            "due_date": sub["next_billing_date"],
            "details": sub,
        }]

    def evaluate_warranty(self, warranty: dict) -> list:
        """Warranty rule: check coverage near expiry."""
        if not warranty.get("warranty_expires"):
            return []
        days_left = self._days_until(warranty["warranty_expires"])
        if days_left > 90 or days_left < -365:
            return []
        priority = self._priority_for_days_left(days_left, URGENT_WARRANTY_DAYS)
        product = warranty.get("product") or "product"
        return [{
            "action": "check_warranty",
            "title": f"{product} warranty expires {warranty['warranty_expires']}",
            "priority": priority,
            "due_date": warranty["warranty_expires"],
            "details": warranty,
        }]
