"""Abstract base classes for document ingestion."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Document:
    """Normalized internal document format."""
    type: str  # receipt | subscription | warranty | appointment | text | email
    content: str
    source: str
    date: Optional[datetime] = None
    attachments: list = field(default_factory=list)


class DocumentParser:
    """Base class for all document parsers."""

    def parse(self, file_path: str) -> Document:
        raise NotImplementedError
