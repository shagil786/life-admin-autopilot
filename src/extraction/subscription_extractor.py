"""Subscription extractor: name, amount, cycle, next billing date."""
import re
from typing import Optional
from src.extraction.base import BaseExtractor
from src.ingestion.base import Document

NAME_PATTERN = r"([A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*)?)\s+subscription"
AMOUNT_PATTERN = r"\$\s*([\d,]+\.?\d*)\s*(?:/|per\s|monthly|yearly|annually)?"
MONTHLY_PATTERN = r"\$\s*([\d,]+\.?\d*)\s*(?:/month|/monthly|monthly)"
YEARLY_PATTERN = r"\$\s*([\d,]+\.?\d*)\s*(?:/year|/yearly|yearly|/annually)"
RENEW_PATTERN = r"renew(?:s|al|ing)?\w*\s*(?:on|date)?\s*:?\s*(\d{4}-\d{2}-\d{2})"


class SubscriptionExtractor(BaseExtractor):
    def extract(self, doc: Document) -> dict:
        content = doc.content
        amount, cycle = self._extract_amount_and_cycle(content)
        return {
            "name": self._extract_name(content),
            "amount": amount,
            "billing_cycle": cycle,
            "next_billing_date": self._extract_next_date(content),
            "source": doc.source,
        }

    def _extract_name(self, text: str) -> Optional[str]:
        match = re.search(NAME_PATTERN, text)
        return match.group(1).strip() if match else None

    def _extract_amount_and_cycle(self, text: str) -> tuple:
        monthly = re.search(MONTHLY_PATTERN, text, re.IGNORECASE)
        if monthly:
            return float(monthly.group(1).replace(",", "")), "monthly"
        yearly = re.search(YEARLY_PATTERN, text, re.IGNORECASE)
        if yearly:
            return float(yearly.group(1).replace(",", "")), "yearly"
        generic = re.search(AMOUNT_PATTERN, text)
        if generic:
            return float(generic.group(1).replace(",", "")), None
        return None, None

    def _extract_next_date(self, text: str) -> Optional[str]:
        match = re.search(RENEW_PATTERN, text, re.IGNORECASE)
        return match.group(1) if match else None
