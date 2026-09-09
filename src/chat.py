#!/usr/bin/env python
"""Conversational REPL for Life Admin Autopilot (Strands Agent).

Includes agentic guardrails: input filtering, per-turn observability
logs (tools, tokens, latency), and loop/budget caps.
"""
import sys
import time

from src.agent.model_factory import build_agent, get_model_id
from src.agent.prompts import SYSTEM_PROMPT
from src.agent.guardrails import check_input, MAX_TURNS
from src.agent.observe import TurnLog, AgentLogger, ObservingCallbackHandler
from src.agent.tools import (
    scan_documents,
    draft_action_message,
    find_cheaper_alternatives,
    search_documents,
    get_today,
    set_active_turn_log,
)


def run_turn(agent, prompt: str, logger: AgentLogger) -> str:
    """One agent turn with observability + budget limits."""
    from strands.types.agent import Limits

    turn = TurnLog(prompt=prompt, model=get_model_id())
    handler = ObservingCallbackHandler(turn)
    set_active_turn_log(turn)  # tools trace into this turn
    start = time.monotonic()
    try:
        result = agent(
            prompt,
            limits=Limits(turns=MAX_TURNS, output_tokens=4096),
            callback_handler=handler,
        )
        metrics = getattr(result, "metrics", None)
        usage = getattr(metrics, "accumulated_usage", None) or {}
        input_tokens = usage.get("inputTokens", 0)
        output_tokens = usage.get("outputTokens", 0)
        output = str(result)
        stop = getattr(result, "stop_reason", "end_turn")
    except Exception as e:
        output = f"(agent error: {e})"
        input_tokens = output_tokens = 0
        stop = "error"
    turn.finish(
        output=output, stop_reason=str(stop),
        input_tokens=input_tokens, output_tokens=output_tokens,
        latency_ms=(time.monotonic() - start) * 1000,
    )
    if turn.has_loop():
        turn.output = output + "\n[loop detected and turn halted]"
    logger.add(turn)
    set_active_turn_log(None)
    return turn.output


def main() -> int:
    print("Life Admin Autopilot — agent chat (Ctrl-C to exit)")
    print("Try: 'scan my documents' or 'what needs my attention?'")
    print("Logs: data/agent_log.jsonl | guardrails + limits on\n")
    logger = AgentLogger(log_dir="data")
    try:
        agent = build_agent(
            SYSTEM_PROMPT,
            tools=[scan_documents, draft_action_message,
                   find_cheaper_alternatives, search_documents, get_today],
        )
    except Exception as e:
        print(f"Could not start agent: {e}", file=sys.stderr)
        print(
            "Set LIFE_ADMIN_BASE_URL, LIFE_ADMIN_API_KEY, LIFE_ADMIN_MODEL "
            "in .env or the environment.",
            file=sys.stderr,
        )
        return 1

    while True:
        try:
            prompt = input("you> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nbye!")
            return 0
        if not prompt:
            continue
        if prompt.lower() in ("exit", "quit"):
            print("bye!")
            print(f"\nSession summary: {logger.summary()}")
            return 0
        ok, reason = check_input(prompt)
        if not ok:
            print(f"\nguardrail> {reason}\n")
            continue
        try:
            reply = run_turn(agent, prompt, logger)
            print(f"\nagent> {reply}\n")
        except KeyboardInterrupt:
            print("\n(interrupted)")
        except Exception as e:
            print(f"\nerror> {e}\n")


if __name__ == "__main__":
    sys.exit(main())
