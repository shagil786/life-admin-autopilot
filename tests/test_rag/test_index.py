"""Tests for the RAG index — hybrid retrieval, metadata filtering, citations."""
import pytest
from src.rag.index import DocumentIndex


@pytest.fixture
def index():
    idx = DocumentIndex()
    idx.add_chunks([
        {"id": "a.txt#0", "text": "Netflix subscription $15.99/month, renews 2026-09-12",
         "source": "a.txt", "doc_type": "subscription", "index": 0},
        {"id": "b.txt#0", "text": "Amazon purchase $89.99 Sony WH-1000XM4 headphones on 2026-08-15",
         "source": "b.txt", "doc_type": "receipt", "index": 0},
        {"id": "c.txt#0", "text": "Dell XPS 15 purchased 2024-11-08, 2 year warranty",
         "source": "c.txt", "doc_type": "warranty", "index": 0},
        {"id": "d.txt#0", "text": "Call mom, buy milk, water the plants",
         "source": "d.txt", "doc_type": "text", "index": 0},
    ])
    return idx


def test_keyword_retrieval(index):
    results = index.search("Netflix renewal")
    assert results[0]["chunk"]["id"] == "a.txt#0"
    assert results[0]["score"] > 0


def test_semantic_word_match(index):
    # "headphones" matches the Amazon chunk even though query differs
    results = index.search("headphones warranty")
    assert any(r["chunk"]["id"] == "b.txt#0" for r in results[:2])


def test_metadata_filter_doc_type(index):
    results = index.search("warranty", doc_type="warranty")
    assert all(r["chunk"]["doc_type"] == "warranty" for r in results)
    assert results  # Dell chunk must be found


def test_metadata_filter_excludes(index):
    results = index.search("warranty", doc_type="receipt")
    ids = [r["chunk"]["id"] for r in results]
    assert "c.txt#0" not in ids


def test_no_results_for_gibberish(index):
    assert index.search("xyzzyplugh") == []


def test_citations_included(index):
    results = index.search("Netflix")
    assert results[0]["citation"] == "a.txt#0"


def test_empty_index():
    idx = DocumentIndex()
    assert idx.search("anything") == []


def test_hybrid_beats_noise(index):
    # The noise chunk mentions nothing relevant — must rank below real docs
    results = index.search("subscription amount Netflix")
    ids = [r["chunk"]["id"] for r in results]
    assert ids[0] == "a.txt#0"
    assert "d.txt#0" not in ids[:3] or results[-1]["chunk"]["id"] == "d.txt#0"


def test_rebuild_replaces(index):
    index.add_chunks([
        {"id": "z.txt#0", "text": "fresh content", "source": "z.txt",
         "doc_type": None, "index": 0},
    ])
    # both old and new searchable
    assert index.search("Netflix")[0]["chunk"]["id"] == "a.txt#0"
    assert index.search("fresh")[0]["chunk"]["id"] == "z.txt#0"
