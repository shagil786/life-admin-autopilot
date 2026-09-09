"""Tests for warranty extractor."""
from src.extraction.warranty_extractor import WarrantyExtractor
from src.ingestion.base import Document


def make_doc(text):
    return Document(type="warranty", content=text, source="test.txt")


def test_finds_product_and_duration():
    doc = make_doc("Sony WH-1000XM5 purchased 2024-06-01, 2 year warranty")
    result = WarrantyExtractor().extract(doc)
    assert result["product"] == "Sony WH-1000XM5"
    assert result["warranty_years"] == 2
    assert result["purchase_date"] == "2024-06-01"


def test_expiration_computed():
    doc = make_doc("Sony WH-1000XM5 purchased 2024-06-01, 2 year warranty")
    result = WarrantyExtractor().extract(doc)
    assert result["warranty_expires"] == "2026-06-01"


def test_missing_fields():
    doc = make_doc("nothing useful")
    result = WarrantyExtractor().extract(doc)
    assert result["product"] is None
    assert result["warranty_years"] is None
