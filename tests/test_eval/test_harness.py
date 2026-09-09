"""Evaluation harness tests.

The test cases themselves double as the evaluation dataset — evaluating
the evaluators first (meta, but necessary).
"""
from src.eval_harness import datasets
from src.eval_harness.retrieval_eval import evaluate_retrieval
from src.eval_harness.extraction_eval import evaluate_extraction


def test_retrieval_dataset_well_formed():
    cases = datasets.RETRIEVAL_CASES
    assert len(cases) >= 8
    for case in cases:
        assert "query" in case and "expected_source" in case
        assert case["query"].strip()


def test_extraction_dataset_well_formed():
    cases = datasets.EXTRACTION_CASES
    assert len(cases) >= 5
    for case in cases:
        assert "text" in case and "expected" in case
        # expected must use only keys the pipeline can produce
        for key in case["expected"]:
            assert key in {
                "vendor", "amount", "date", "product",
                "warranty_years", "billing_cycle", "next_billing_date",
                "name", "purchase_date", "warranty_expires",
            }


def test_retrieval_eval_returns_metrics():
    metrics = evaluate_retrieval(k=3)
    assert 0.0 <= metrics["hit_rate_at_k"] <= 1.0
    assert 0.0 <= metrics["mrr"] <= 1.0
    assert metrics["cases"] == len(datasets.RETRIEVAL_CASES)


def test_retrieval_eval_hits_sample_data():
    # Sanity: Netflix queries should hit on our samples
    metrics = evaluate_retrieval(k=3)
    assert metrics["hit_rate_at_k"] >= 0.5  # majority should hit


def test_extraction_eval_returns_metrics():
    metrics = evaluate_extraction()
    assert 0.0 <= metrics["field_precision"] <= 1.0
    assert 0.0 <= metrics["field_recall"] <= 1.0
    assert metrics["documents"] == len(datasets.EXTRACTION_CASES)


def test_extraction_eval_reasonable_accuracy():
    # Spec target: 80%+ extraction on clean docs; regex-only should do well
    metrics = evaluate_extraction()
    assert metrics["field_recall"] >= 0.7
