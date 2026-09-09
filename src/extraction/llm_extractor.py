"""LLM-powered extraction for messy documents.

Follows the BaseExtractor interface so the Pipeline can use it as a
fallback when regex extractors come up empty. The LLM is injectable:
pass anything with a complete(prompt) -> str method.
"""
import json
import re
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

    def __init__(self, llm: Optional[CompletionLLM] = None, retries: int = 3):
        self._llm = llm
        self._retries = retries

    def extract(self, doc: Document) -> dict:
        if not self._llm or not doc.content.strip():
            return {}
        for attempt in range(3):
            try:
                raw = self._llm.complete(EXTRACTION_PROMPT + doc.content)
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
                cleaned["source"] = doc.source
                return cleaned
            # all-null or empty result: the free-tier model is flaky — retry
        return {}

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
