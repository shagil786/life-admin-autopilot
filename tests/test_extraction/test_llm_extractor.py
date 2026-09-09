"""Tests for LLM extractor (offline — mock the LLM)."""
import pytest

from src.extraction.llm_extractor import LLMExtractor
from src.ingestion.base import Document


class MockLLM:
    """Returns a canned response, records prompts."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def make_doc(text, type_="receipt", source="messy.txt"):
    return Document(type=type_, content=text, source=source)


def test_extracts_structured_json():
    llm = MockLLM(['{"vendor": "Acme Corp", "amount": 129.50, "date": "2026-08-30"}'])
    ext = LLMExtractor(llm=llm)
    doc = make_doc("some messy scanned text ... paid at ACME ... total 129.5")
    result = ext.extract(doc)
    assert result["vendor"] == "Acme Corp"
    assert result["amount"] == 129.50
    assert result["date"] == "2026-08-30"


def test_passes_document_content_in_prompt():
    llm = MockLLM(["{}"])
    ext = LLMExtractor(llm=llm)
    doc = make_doc("UNIQUE-MARKER-123")
    ext.extract(doc)
    assert "UNIQUE-MARKER-123" in llm.prompts[0]


def test_tolerates_markdown_fences():
    llm = MockLLM(['```json\n{"vendor": "X", "amount": 1.0}\n```'])
    ext = LLMExtractor(llm=llm)
    result = ext.extract(make_doc("text"))
    assert result["vendor"] == "X"


def test_tolerates_prose_around_json():
    llm = MockLLM(['Sure! Here you go: {"vendor": "Y", "amount": 2.0} hope that helps'])
    ext = LLMExtractor(llm=llm)
    result = ext.extract(make_doc("text"))
    assert result["vendor"] == "Y"


def test_invalid_json_returns_empty():
    llm = MockLLM(["sorry, I cannot parse that"])
    ext = LLMExtractor(llm=llm)
    result = ext.extract(make_doc("text"))
    assert result == {}


def test_source_preserved():
    llm = MockLLM(['{"vendor": "Z"}'])
    ext = LLMExtractor(llm=llm)
    result = ext.extract(make_doc("text", source="doc.pdf"))
    assert result["source"] == "doc.pdf"


def test_missing_llm_returns_empty():
    ext = LLMExtractor(llm=None)
    assert ext.extract(make_doc("text")) == {}
