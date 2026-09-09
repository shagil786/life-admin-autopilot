"""Tests for the RAG service (ingest + retrieve with citations)."""
from datetime import date

import pytest
from src.rag.service import RagService


@pytest.fixture
def service():
    svc = RagService(samples_dir="data/samples")
    svc.ingest()
    return svc


def test_ingest_indexes_samples(service):
    assert service.index.size >= 6  # 7 sample docs, some multi-chunk


def test_query_finds_netflix(service):
    results = service.query("Netflix subscription renewal")
    assert results
    assert "netflix" in results[0]["citation"].lower() or \
        "Netflix" in results[0]["chunk"]["text"]


def test_query_returns_citations(service):
    for r in service.query("warranty"):
        assert r["citation"].count("#") == 1
        assert r["chunk"]["source"]


def test_context_construction_limited(service):
    ctx = service.build_context("Netflix", max_chars=200)
    assert len(ctx) <= 220  # roughly respected
    assert "#" in ctx  # citations present


def test_context_ordered_by_relevance(service):
    ctx = service.build_context("Netflix renews when?")
    # top result should appear early in the context
    top = service.query("Netflix renews when?")[0]
    assert top["chunk"]["text"][:30] in ctx[:400]


def test_query_with_doc_type_filter(service):
    results = service.query("warranty", doc_type="warranty")
    assert results
    for r in results:
        assert r["chunk"]["doc_type"] == "warranty"


def test_answer_only_from_context_prompt(service):
    from src.rag.service import HALLUCINATION_GUARD
    assert "only" in HALLUCINATION_GUARD.lower()
    assert "context" in HALLUCINATION_GUARD.lower()
