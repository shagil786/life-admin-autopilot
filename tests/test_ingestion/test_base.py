"""Tests for ingestion base classes."""
from src.ingestion.base import Document, DocumentParser


def test_document_creation():
    doc = Document(type="receipt", content="test", source="file.pdf")
    assert doc.type == "receipt"
    assert doc.content == "test"
    assert doc.source == "file.pdf"
    assert doc.date is None
    assert doc.attachments == []


def test_document_parser_base_raises():
    parser = DocumentParser()
    try:
        parser.parse("anything")
        assert False, "should have raised"
    except NotImplementedError:
        pass
