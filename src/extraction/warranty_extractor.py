"""Warranty extractor: product, purchase date, warranty length, expiry."""
import re
from datetime import date, timedelta
from typing import Optional
from src.extraction.base import BaseExtractor
from src.ingestion.base import Document

PRODUCT_PATTERN = r"^([A-Z][\w&.'-]*(?:\s+[A-Z]?[\w&.'-]*)*?)\s+purchased"
DATE_PATTERN = r"purchased\s+(\d{4}-\d{2}-\d{2})"
YEARS_PATTERN = r"(\d+)\s*year"
MONTHS_PATTERN = r"(\d+)\s*month"


class WarrantyExtractor(BaseExtractor):
    def extract(self, doc: Document) -> dict:
        content = doc.content
        purchase_date = self._extract_purchase_date(content)
        years = self._extract_years(content)
        return {
            "product": self._extract_product(content),
            "purchase_date": purchase_date,
            "warranty_years": years,
            "warranty_expires": self._compute_expiry(purchase_date, content),
            "source": doc.source,
        }

    def _extract_product(self, text: str) -> Optional[str]:
        match = re.search(PRODUCT_PATTERN, text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_purchase_date(self, text: str) -> Optional[str]:
        match = re.search(DATE_PATTERN, text, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_years(self, text: str) -> Optional[int]:
        match = re.search(YEARS_PATTERN, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        months = re.search(MONTHS_PATTERN, text, re.IGNORECASE)
        if months:
            m = int(months.group(1))
            return m / 12 if m % 12 else m // 12
        return None

    def _compute_expiry(self, purchase_date: Optional[str], text: str) -> Optional[str]:
        if not purchase_date:
            return None
        try:
            start = date.fromisoformat(purchase_date)
        except ValueError:
            return None
        years_match = re.search(YEARS_PATTERN, text, re.IGNORECASE)
        if years_match:
            end = start.replace(year=start.year + int(years_match.group(1)))
        else:
            months_match = re.search(MONTHS_PATTERN, text, re.IGNORECASE)
            if not months_match:
                return None
            months = int(months_match.group(1))
            end = start + timedelta(days=30 * months)
        return end.isoformat()
