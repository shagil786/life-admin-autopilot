"""Plain text document parser."""
from src.ingestion.base import Document, DocumentParser


class TextParser(DocumentParser):
    """Parses .txt files into normalized Documents."""

    def parse(self, file_path: str) -> Document:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return Document(type="text", content=content, source=file_path)
