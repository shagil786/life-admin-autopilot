"""Tests for PDF parser."""
import pytest
from src.ingestion.pdf_parser import PDFParser


def test_pdf_parser_returns_document(tmp_path):
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    pdf_path = tmp_path / "sample_receipt.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 700, "Amazon purchase $49.99 on 2024-01-15")
    c.save()

    doc = PDFParser().parse(str(pdf_path))
    assert doc.type == "receipt"
    assert len(doc.content) > 0
