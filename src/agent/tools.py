"""Strands tools wrapping the life-admin pipeline for the agent."""
import time
from datetime import date

from strands import tool

from src.main import Pipeline
from src.output.message_drafter import MessageDrafter
from src.extraction.gateway_llm import build_gateway_llm
from src.task_engine.rules import RuleEngine
from src.task_engine.scheduler import TaskScheduler
from src.task_engine.alternative_finder import (
    AlternativeFinder,
    build_llm_search_fn,
    format_alternatives,
)
from src.rag.service import RagService, HALLUCINATION_GUARD
from src.agent.guardrails import validate_tool_args, _DOC_TYPES

def _validated(tool_name: str, args: dict, fn):
    """Run a tool body only after arg validation; structured error back
    to the LLM so it can retry with corrected args. Traces the call into
    the active turn log (observability hook)."""
    ok, err = validate_tool_args(tool_name, args)
    if not ok:
        _trace(tool_name, args, f"Invalid args: {err}", ok=False)
        return f"Invalid arguments for {tool_name}: {err}. Call again with corrected arguments."
    start = time.monotonic()
    try:
        result = fn()
        _trace(tool_name, args, result, ok=True,
               latency_ms=(time.monotonic() - start) * 1000)
        return result
    except Exception as e:
        _trace(tool_name, args, f"Error: {e}", ok=False,
               latency_ms=(time.monotonic() - start) * 1000)
        return f"Tool error in {tool_name}: {e}. The agent can retry or report this to the user."


# Active-turn tracing: chat.run_turn registers the current TurnLog here.
_active_turn_log = None


def set_active_turn_log(turn_log):
    global _active_turn_log
    _active_turn_log = turn_log


def _trace(tool_name, args, result, ok, latency_ms=0.0):
    if _active_turn_log is not None:
        _active_turn_log.record_tool(tool_name, args=args, result=result,
                                     ok=ok, latency_ms=latency_ms)


# Module-level state so tools share one pipeline instance.
_pipeline: Pipeline = None
_drafter = MessageDrafter()
_rag: RagService = None


def _get_rag() -> RagService:
    global _rag
    if _rag is None:
        _rag = RagService(samples_dir="data/samples")
        _rag.ingest()
    return _rag


def _get_pipeline() -> Pipeline:
    global _pipeline
    if _pipeline is None:
        today = date.today()
        _pipeline = Pipeline(
            rules=RuleEngine(today=today),
            scheduler=TaskScheduler(today=today),
            llm=build_gateway_llm(),
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
    def _run():
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
        # Append machine-readable details so the agent can act on specifics
        # (product names, vendors, amounts) without re-asking the user.
        detail_lines = ["\n--- task details ---"]
        for i, task in enumerate(result["tasks"], 1):
            d = task.get("details", {})
            keep = {k: v for k, v in d.items() if k != "source"}
            detail_lines.append(f"{i}. {keep}")
        return result["formatted"] + f"\n\n{result['summary']}" + "\n".join(detail_lines)

    return _validated("scan_documents", {"path": path}, _run)


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
    def _run():
        if action == "cancel_or_review":
            return _drafter.draft_cancellation(
                {"name": name, "amount": amount, "billing_cycle": "month"}
            )
        if action == "return_or_exchange":
            return _drafter.draft_return(
                {"vendor": name, "amount": amount, "date": date_str or None}
            )
        return f"Unknown action '{action}'. Use cancel_or_review or return_or_exchange."

    return _validated(
        "draft_action_message",
        {"action": action, "name": name, "amount": amount},
        _run,
    )


@tool(
    description=(
        "Find cheaper alternatives to a product the user bought or is about "
        "to buy. Provide the product name and its price as the budget. "
        "Returns sorted alternatives with reasons. Requires the LLM "
        "gateway to be configured; says so otherwise."
    )
)
def find_cheaper_alternatives(product: str, current_price: float) -> str:
    """Search for cheaper alternatives to a product."""
    def _run():
        search_fn = build_llm_search_fn()
        if search_fn is None:
            return (
                "No search gateway configured — set LIFE_ADMIN_BASE_URL and "
                "LIFE_ADMIN_API_KEY to enable cheaper-alternative search."
            )
        finder = AlternativeFinder(search_fn=search_fn)
        alts = finder.find(product, max_price=current_price)
        if not alts:
            return f"No cheaper alternatives found for {product} within ${current_price:.2f}."
        return format_alternatives(product, alts)

    return _validated(
        "find_cheaper_alternatives",
        {"product": product, "current_price": current_price},
        _run,
    )


@tool(
    description=(
        "Search the user's ingested documents (receipts, subscriptions, "
        "warranties, emails) and return relevant chunks WITH citations. "
        "Use for questions like 'when did I buy X', 'what did the Y email "
        "say', 'how much was Z'. Chunks cite their source like "
        "file.txt#0 — always show these citations in your answer."
    )
)
def search_documents(query: str, doc_type: str = "") -> str:
    """Hybrid retrieval over ingested docs. Returns cited chunks."""
    def _run():
        rag = _get_rag()
        dtype = doc_type if doc_type in _DOC_TYPES else None
        results = rag.query(query, doc_type=dtype, top_k=5)
        if not results:
            return f"No documents matched {query!r}. The index may need re-ingesting."
        lines = [f"{len(results)} matching chunks (best first):"]
        for r in results:
            c = r["chunk"]
            lines.append(
                f"\n[{r['citation']}] (score {r['score']}, type {c.get('doc_type')})"
                f"\n{c['text']}"
            )
        lines.append(f"\n{HALLUCINATION_GUARD}")
        return "\n".join(lines)

    return _validated(
        "search_documents", {"query": query, "doc_type": doc_type}, _run
    )


@tool(
    description=(
        "Get today's date, for reasoning about return windows, renewal "
        "deadlines, and warranty expiry."
    )
)
def get_today() -> str:
    return date.today().isoformat()
