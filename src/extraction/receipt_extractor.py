"""Receipt extractor: vendor, amount, date."""
import re
from typing import Optional
from src.extraction.base import BaseExtractor
from src.ingestion.base import Document

VENDOR_PATTERNS = [
    # "purchased from Amazon" / "bought at Best Buy" / "via Walmart"
    r"(?:from|at|via)\s+([A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*)*)",
    # First capitalized words at start of doc: "Amazon purchase ..."
    r"^([A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*)*)",
]
AMOUNT_PATTERN = r"\$\s*([\d,]+\.?\d*)"
DATE_PATTERN = r"(\d{4}-\d{2}-\d{2})"


class ReceiptExtractor(BaseExtractor):
    def extract(self, doc: Document) -> dict:
        content = doc.content
        return {
            "vendor": self._extract_vendor(content),
            "amount": self._extract_amount(content),
            "date": self._extract_date(content),
            "source": doc.source,
        }

    def _extract_vendor(self, text: str) -> Optional[str]:
        for pattern in VENDOR_PATTERNS:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_amount(self, text: str) -> Optional[float]:
        match = re.search(AMOUNT_PATTERN, text)
        if match:
            return float(match.group(1).replace(",", ""))
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        match = re.search(DATE_PATTERN, text)
        return match.group(1) if match else None
