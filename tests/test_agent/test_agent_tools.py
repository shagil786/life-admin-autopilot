"""Tests for agent layer — offline (no LLM calls)."""
import pytest


def test_system_prompt_safety_rules():
    from src.agent.prompts import SYSTEM_PROMPT

    assert "NEVER" in SYSTEM_PROMPT
    assert "sent an email" in SYSTEM_PROMPT
    assert "draft" in SYSTEM_PROMPT.lower()


def test_scan_documents_tool_registered():
    from src.agent.tools import scan_documents

    assert scan_documents.tool_name == "scan_documents"
    assert "description" in str(scan_documents.tool_spec)


def test_scan_documents_tool_runs():
    from src.agent.tools import scan_documents

    result = scan_documents(path="data/samples")
    assert "URGENT" in result
    assert "Netflix" in result


def test_draft_action_message_cancel():
    from src.agent.tools import draft_action_message

    msg = draft_action_message(
        action="cancel_or_review", name="Netflix", amount=15.99
    )
    assert "Netflix" in msg
    assert "cancel" in msg.lower()


def test_draft_action_message_return():
    from src.agent.tools import draft_action_message

    msg = draft_action_message(
        action="return_or_exchange", name="Amazon", amount=89.99,
        date_str="2026-08-20",
    )
    assert "Amazon" in msg
    assert "[ORDER ID]" in msg


def test_draft_action_message_unknown_action():
    from src.agent.tools import draft_action_message

    # Guardrail rejects invalid action BEFORE execution, structured for retry
    msg = draft_action_message(action="explode", name="X")
    assert "Invalid arguments" in msg
    assert "cancel_or_review" in msg  # tells the LLM the valid options


def test_get_today():
    from src.agent.tools import get_today

    assert get_today().count("-") == 2  # ISO date


def test_model_factory_env_config(monkeypatch):
    import os
    from src.agent.model_factory import _env

    # Use a variable that .env never defines
    monkeypatch.setenv("LIFE_ADMIN_TEST_VAR", "from-env")
    assert _env("LIFE_ADMIN_TEST_VAR", "default") == "from-env"
    monkeypatch.delenv("LIFE_ADMIN_TEST_VAR")
    assert _env("LIFE_ADMIN_TEST_VAR", "default") == "default"
    # Defaults are applied when nothing is set
    assert _env("LIFE_ADMIN_TEST_VAR", "fallback") == "fallback"
