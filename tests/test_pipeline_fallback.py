"""Tests for the pipeline's LLM fallback extraction (mocked LLM)."""
from datetime import date

from src.main import Pipeline
from src.task_engine.rules import RuleEngine
from src.task_engine.scheduler import TaskScheduler


class MockLLM:
    def __init__(self, response):
        self.response = response
        self.called = 0

    def complete(self, prompt):
        self.called += 1
        return self.response


def make_pipeline(llm):
    today = date(2026, 9, 10)
    return Pipeline(
        rules=RuleEngine(today=today),
        scheduler=TaskScheduler(today=today),
        llm=llm,
    )


def test_llm_fallback_on_messy_receipt(tmp_path):
    # Messy text the regex extractors can't parse
    f = tmp_path / "messy.txt"
    f.write_text("TOTAL DUE ... $249.00 ... Acme Furniture ... 08/30/26 paid")

    llm = MockLLM('{"vendor": "Acme Furniture", "amount": 249.0, "date": "2026-08-30"}')
    result = make_pipeline(llm).run([str(f)])

    titles = " ".join(t["title"] for t in result["tasks"])
    assert "Acme Furniture" in titles


def test_no_llm_call_when_regex_matches(tmp_path):
    f = tmp_path / "clean.txt"
    f.write_text("Amazon purchase $49.99 on 2026-08-30")

    llm = MockLLM("{}")
    make_pipeline(llm).run([str(f)])
    assert llm.called == 0


def test_llm_fallback_subscription(tmp_path):
    f = tmp_path / "messy_sub.txt"
    f.write_text("RENEWAL NOTICE — Premium Plan — auto-pay $9.99 — next charge in 3 days")

    llm = MockLLM(
        '{"vendor": "Premium Plan", "amount": 9.99, "billing_cycle": "monthly", '
        '"next_billing_date": "2026-09-13"}'
    )
    result = make_pipeline(llm).run([str(f)])

    assert any(t["action"] == "cancel_or_review" for t in result["tasks"])


def test_llm_fallback_warranty(tmp_path):
    f = tmp_path / "warranty_card.txt"
    f.write_text("Warranty card — Whirlpool fridge — bought fall 2023 — covered 3 yrs")

    llm = MockLLM(
        '{"product": "Whirlpool fridge", "warranty_years": 3, '
        '"date": "2023-09-15"}'
    )  # expires 2026-09-15 — 5 days from the pipeline's today
    result = make_pipeline(llm).run([str(f)])

    assert any(t["action"] == "check_warranty" for t in result["tasks"])


def test_llm_failure_is_silent(tmp_path):
    f = tmp_path / "garbage.txt"
    f.write_text("complete garbage that nothing can parse")

    llm = MockLLM("not json at all")
    result = make_pipeline(llm).run([str(f)])
    assert result["tasks"] == []
