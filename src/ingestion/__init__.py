"""Ingestion package: PDF, text, and email parsers."""
from src.ingestion.base import Document, DocumentParser
from src.ingestion.text_parser import TextParser

__all__ = ["Document", "DocumentParser", "TextParser"]
