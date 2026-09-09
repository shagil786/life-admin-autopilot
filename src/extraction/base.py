"""Base class for extractors."""
from src.ingestion.base import Document


class BaseExtractor:
    """Extracts structured data from a Document."""

    def extract(self, doc: Document) -> dict:
        raise NotImplementedError
