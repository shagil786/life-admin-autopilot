"""Tests for agent guardrails: input filtering, arg validation, limits."""
import pytest

from src.agent.guardrails import (
    check_input,
    validate_tool_args,
    MAX_TURNS,
)


def test_on_topic_passes():
    ok, msg = check_input("when does netflix renew?")
    assert ok is True


def test_off_topic_rejected():
    ok, msg = check_input("write me a python script to hack a website")
    assert ok is False
    assert "life admin" in msg.lower()


def test_life_admin_keywords_pass():
    for prompt in [
        "what needs my attention",
        "draft a return message for amazon",
        "cheaper alternatives to these headphones",
        "what did the warranty card say",
        "cancel my gym subscription",
    ]:
        ok, _ = check_input(prompt)
        assert ok is True, prompt


def test_borderline_finance_question_passes():
    # finance questions are in-scope (subscriptions, bills)
    ok, _ = check_input("how much do I spend on subscriptions?")
    assert ok is True


def test_validate_tool_args_scan_documents():
    # valid
    ok, err = validate_tool_args("scan_documents", {"path": "data/samples"})
    assert ok
    # path must be a string, not a number
    ok, err = validate_tool_args("scan_documents", {"path": 42})
    assert not ok and "path" in err
    # missing optional arg is fine (default exists)
    ok, err = validate_tool_args("scan_documents", {})
    assert ok


def test_validate_tool_args_draft_action_message():
    ok, err = validate_tool_args(
        "draft_action_message",
        {"action": "cancel_or_review", "name": "Netflix", "amount": 15.99},
    )
    assert ok
    # amount must be a number if present
    ok, err = validate_tool_args(
        "draft_action_message",
        {"action": "cancel_or_review", "name": "X", "amount": "free"},
    )
    assert not ok and "amount" in err
    # unknown action rejected
    ok, err = validate_tool_args(
        "draft_action_message", {"action": "detonate", "name": "X"}
    )
    assert not ok and "action" in err


def test_validate_tool_args_search_documents():
    ok, err = validate_tool_args(
        "search_documents", {"query": "netflix", "doc_type": "subscription"}
    )
    assert ok
    ok, err = validate_tool_args("search_documents", {"query": ""})
    assert not ok and "query" in err
    ok, err = validate_tool_args(
        "search_documents", {"query": "x", "doc_type": "bogus"}
    )
    assert not ok and "doc_type" in err


def test_validate_tool_args_find_cheaper():
    ok, err = validate_tool_args(
        "find_cheaper_alternatives",
        {"product": "Sony WH-1000XM4", "current_price": 89.99},
    )
    assert ok
    ok, err = validate_tool_args(
        "find_cheaper_alternatives", {"product": "X", "current_price": -5}
    )
    assert not ok and "price" in err.lower()


def test_validate_tool_args_unknown_tool():
    ok, err = validate_tool_args("nonexistent_tool", {})
    assert not ok


def test_max_turns_reasonable():
    assert 1 <= MAX_TURNS <= 10
