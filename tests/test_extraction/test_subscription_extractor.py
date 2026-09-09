"""Tests for subscription extractor."""
from src.extraction.subscription_extractor import SubscriptionExtractor
from src.ingestion.base import Document


def make_doc(text):
    return Document(type="subscription", content=text, source="test.txt")


def test_finds_name_amount_cycle():
    doc = make_doc("Netflix subscription $15.99/month, renews 2025-01-15")
    result = SubscriptionExtractor().extract(doc)
    assert result["name"] == "Netflix"
    assert result["amount"] == 15.99
    assert result["billing_cycle"] == "monthly"
    assert result["next_billing_date"] == "2025-01-15"


def test_finds_yearly_cycle():
    doc = make_doc("Costco membership $60/year renews 2025-06-01")
    result = SubscriptionExtractor().extract(doc)
    assert result["billing_cycle"] == "yearly"
    assert result["amount"] == 60.0


def test_missing_fields_return_none():
    doc = make_doc("random text")
    result = SubscriptionExtractor().extract(doc)
    assert result["name"] is None
    assert result["amount"] is None
    assert result["next_billing_date"] is None
