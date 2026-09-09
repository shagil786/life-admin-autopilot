"""Agent guardrails: input filtering, tool-arg validation, run limits.

Per agentic-AI best practice:
- validate tool args before execution (LLMs hallucinate parameter values)
- guard inputs to keep the agent on-topic
- cap iterations to prevent runaway loops and costs
"""
from typing import Optional

MAX_TURNS = 6  # hard cap on agent event-loop turns per request

# Keywords that indicate the prompt is within the agent's purpose.
# The agent's job: life admin (returns, subscriptions, warranties,
# appointments, documents, spending questions).
_ON_TOPIC = (
    "return", "subscription", "renew", "cancel", "warranty", "guarantee",
    "receipt", "invoice", "bill", "appointment", "schedule", "deadline",
    "task", "task", "document", "email", "netflix", "spotify", "gym",
    "membership", "purchase", "bought", "buy", "price", "cheaper",
    "alternative", "refund", "attention", "scan", "draft", "reminder",
    "payment", "charge", "spend", "save", "money", "owes", "due",
    "urgent", "warranty", "receipt", "products", "shopping",
    "renewal", "vendor", "amazon", "costco", "best buy",
)

_DOC_TYPES = {"receipt", "subscription", "warranty", "email", "text"}
_ACTIONS = {"cancel_or_review", "return_or_exchange"}


def check_input(prompt: str) -> tuple:
    """Return (ok, reason). Reject clearly off-topic requests.

    Deliberately permissive: personal-ops questions are broad, so we
    reject only requests that are clearly outside life-admin work AND
    match known off-topic intents (code writing, hacking, etc.).
    """
    p = prompt.lower()
    if any(k in p for k in _ON_TOPIC):
        return True, ""
    clearly_off = (
        ("hack" in p or "exploit" in p),
        ("write" in p and ("code" in p or "script" in p or "essay" in p)),
        ("recipe" in p or "cook" in p),
        ("weather" in p),
        ("translate" in p),
    )
    if any(clearly_off):
        return False, (
            "That's outside my job — I'm Life Admin Autopilot and only "
            "handle life-admin tasks: returns, subscriptions, warranties, "
            "appointments, and questions about your documents."
        )
    # default: allow (better to try than to wrongly refuse)
    return True, ""


def validate_tool_args(tool: str, args: dict) -> tuple:
    """Return (ok, error_message). Validate tool args before execution."""
    if tool == "scan_documents":
        if "path" in args and not isinstance(args.get("path"), (str, type(None))):
            return False, "path must be a string folder/file path"
        return True, ""

    if tool == "draft_action_message":
        action = args.get("action")
        if action not in _ACTIONS:
            return False, (
                f"action must be one of {sorted(_ACTIONS)}, got {action!r}"
            )
        if not args.get("name"):
            return False, "name is required"
        amount = args.get("amount", 0)
        if not isinstance(amount, (int, float)):
            return False, "amount must be a number"
        return True, ""

    if tool == "search_documents":
        if not args.get("query"):
            return False, "query must be a non-empty string"
        dt = args.get("doc_type", "")
        if dt and dt not in _DOC_TYPES:
            return False, f"doc_type must be one of {sorted(_DOC_TYPES)}"
        return True, ""

    if tool == "find_cheaper_alternatives":
        if not args.get("product"):
            return False, "product is required"
        price = args.get("current_price")
        if not isinstance(price, (int, float)) or price < 0:
            return False, "current_price must be a non-negative number"
        return True, ""

    if tool == "get_today":
        return True, ""

    return False, f"unknown tool: {tool}"
