"""LLM-powered extraction for messy documents.

Follows the BaseExtractor interface so the Pipeline can use it as a
fallback when regex extractors come up empty. The LLM is injectable:
pass anything with a complete(prompt) -> str method.
"""
import json
import re
from datetime import date
from typing import Optional, Protocol

from src.extraction.base import BaseExtractor
from src.ingestion.base import Document


class CompletionLLM(Protocol):
    def complete(self, prompt: str) -> str: ...


EXTRACTION_PROMPT = """Extract structured data from this document text.

Return ONLY a JSON object (no markdown, no prose) with any of these keys
that apply, using null for unknown values:
- vendor: store/retailer name
- amount: total price as a number (no currency symbol)
- date: purchase/event date as YYYY-MM-DD. If the document has a partial
  date ("8/30", "Aug 30"), interpret it as the most recent occurrence in
  the past — e.g. if today is 2026-09-10, "8/30" means 2026-08-30, not
  2025-08-30. Never choose a date in the future unless the text clearly
  refers to a future event (like a renewal).
- product: product name
- warranty_years: warranty length in years as a number
- billing_cycle: "monthly" or "yearly" if a subscription amount is mentioned
- next_billing_date: next renewal date as YYYY-MM-DD

Document text:
"""


class LLMExtractor(BaseExtractor):

    _ALLOWED = {
        "vendor", "amount", "date", "product",
        "warranty_years", "billing_cycle", "next_billing_date",
    }

    def __init__(self, llm: Optional[CompletionLLM] = None, retries: int = 3,
                 today: Optional[date] = None):
        self._llm = llm
        self._retries = retries
        self._today = today or date.today()

    def extract(self, doc: Document) -> dict:
        if not self._llm or not doc.content.strip():
            return {}
        for attempt in range(self._retries):
            try:
                prompt = (
                    f"Today's date is {self._today.isoformat()}.\n\n"
                    + EXTRACTION_PROMPT
                    + doc.content
                )
                raw = self._llm.complete(prompt)
                data = self._parse_json(raw)
            except Exception:
                continue  # retry transient gateway errors
            if not isinstance(data, dict):
                continue
            cleaned = {
                k: v
                for k, v in data.items()
                if k in self._ALLOWED and v is not None
            }
            if cleaned:
                cleaned = self._fix_dates(cleaned)
                cleaned["source"] = doc.source
                return cleaned
            # all-null or empty result: the free-tier model is flaky — retry
        return {}

    def _fix_dates(self, data: dict) -> dict:
        """Year-bump heuristic for receipt-like documents only.

        Receipts are recent by nature: a "date" over a year old with the
        same month/day in the last 365 days was probably a wrong-year
        guess by the LLM (partial dates like "8/30"). Warranty purchase
        dates are legitimately old, so skip the bump when warranty_years
        is present. Renewal dates in the future are left alone; past ones
        are bumped to the next occurrence."""
        has_warranty = data.get("warranty_years") is not None
        for key in ("date", "next_billing_date"):
            value = data.get(key)
            if not isinstance(value, str):
                continue
            try:
                d = date.fromisoformat(value)
            except ValueError:
                continue
            if key == "next_billing_date":
                if d >= self._today:
                    continue  # future renewal — correct as-is
                # past renewal: bump to next occurrence within a year
                bumped = d.replace(year=d.year + (age_years := (self._today - d).days // 365) + 1)
                if 0 <= (bumped - self._today).days <= 365:
                    data[key] = bumped.isoformat()
                continue
            # key == "date": only bump receipt-like docs (no warranty info)
            if has_warranty:
                continue
            age_days = (self._today - d).days
            if age_days > 365:
                bumped = d.replace(year=d.year + (age_days // 365))
                if 0 <= (self._today - bumped).days <= 365:
                    data[key] = bumped.isoformat()
        return data

    def _parse_json(self, text: str):
        """Tolerate markdown fences and surrounding prose."""
        text = text.strip()
        if "```" in text:
            for block in text.split("```"):
                candidate = block.strip()
                if candidate.startswith("json"):
                    candidate = candidate[4:].strip()
                if candidate.startswith("{"):
                    text = candidate
                    break
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                text = text[start:end + 1]
        try:
            return json.loads(text)
        except Exception:
            return {}
