"""Retrieval quality evaluation: hit-rate@k and MRR.

Runs the labeled RETRIEVAL_CASES against the RAG index built from
data/samples. Hit = expected doc's chunk appears in top-k; MRR uses
the rank of the first hit.
"""
from src.eval_harness import datasets
from src.rag.service import RagService


def evaluate_retrieval(k: int = 5, samples_dir: str = "data/samples") -> dict:
    rag = RagService(samples_dir=samples_dir)
    rag.ingest()

    hits = 0
    reciprocal_ranks = []
    per_case = []

    for case in datasets.RETRIEVAL_CASES:
        results = rag.query(case["query"], top_k=k)
        expected = case["expected_source"].lower()
        rank = None
        for i, r in enumerate(results, 1):
            if expected in r["citation"].lower():
                rank = i
                break
        hit = rank is not None
        hits += hit
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        per_case.append({
            "query": case["query"],
            "hit": hit,
            "rank": rank,
        })

    n = len(datasets.RETRIEVAL_CASES)
    return {
        "hit_rate_at_k": round(hits / n, 3),
        "mrr": round(sum(reciprocal_ranks) / n, 3),
        "cases": n,
        "k": k,
        "per_case": per_case,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(evaluate_retrieval(), indent=2, default=str))
