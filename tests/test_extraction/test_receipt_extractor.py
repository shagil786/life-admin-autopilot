"""Tests for receipt extractor."""
from src.extraction.receipt_extractor import ReceiptExtractor
from src.ingestion.base import Document


def make_doc(text):
    return Document(type="receipt", content=text, source="test.txt")


def test_finds_vendor_and_amount():
    doc = make_doc("Amazon purchase $49.99 on 2024-01-15")
    result = ReceiptExtractor().extract(doc)
    assert result["vendor"] == "Amazon"
    assert result["amount"] == 49.99


def test_finds_amount_with_commas():
    doc = make_doc("Best Buy total: $1,299.99")
    result = ReceiptExtractor().extract(doc)
    assert result["amount"] == 1299.99


def test_finds_purchase_date():
    doc = make_doc("Amazon purchase $49.99 on 2024-01-15")
    result = ReceiptExtractor().extract(doc)
    assert result["date"] == "2024-01-15"


def test_returns_none_when_missing():
    doc = make_doc("no financial info here")
    result = ReceiptExtractor().extract(doc)
    assert result["vendor"] is None
    assert result["amount"] is None
