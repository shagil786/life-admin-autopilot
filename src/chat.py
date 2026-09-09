#!/usr/bin/env python
"""Conversational REPL for Life Admin Autopilot (Strands Agent)."""
import sys

from src.agent.model_factory import build_agent
from src.agent.prompts import SYSTEM_PROMPT
from src.agent.tools import (
    scan_documents,
    draft_action_message,
    find_cheaper_alternatives,
    search_documents,
    get_today,
)


def main() -> int:
    print("Life Admin Autopilot — agent chat (Ctrl-C to exit)")
    print("Try: 'scan my documents' or 'what needs my attention?'\n")
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
            return 0
        try:
            result = agent(prompt)
            print(f"\nagent> {result}\n")
        except KeyboardInterrupt:
            print("\n(interrupted)")
        except Exception as e:
            print(f"\nerror> {e}\n")


if __name__ == "__main__":
    sys.exit(main())
