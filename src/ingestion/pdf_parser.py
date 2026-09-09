"""PDF document parser using PyPDF2."""
import PyPDF2
from src.ingestion.base import Document, DocumentParser


class PDFParser(DocumentParser):
    """Parses PDF files, extracting raw text."""

    def parse(self, file_path: str) -> Document:
        content = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                content += (page.extract_text() or "") + "\n"
        return Document(type="receipt", content=content.strip(), source=file_path)
