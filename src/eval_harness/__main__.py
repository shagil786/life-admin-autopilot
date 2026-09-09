"""Run all evaluations: retrieval quality + extraction accuracy."""
import json

from src.eval_harness.retrieval_eval import evaluate_retrieval
from src.eval_harness.extraction_eval import evaluate_extraction


def run_all() -> dict:
    return {
        "retrieval": evaluate_retrieval(k=5),
        "extraction": evaluate_extraction(),
    }


if __name__ == "__main__":
    results = run_all()
    r, e = results["retrieval"], results["extraction"]
    print("=" * 50)
    print("EVALUATION REPORT — Life Admin Autopilot")
    print("=" * 50)
    print(f"\nRAG Retrieval ({r['cases']} queries, k={r['k']})")
    print(f"  hit-rate@{r['k']}: {r['hit_rate_at_k']:.1%}")
    print(f"  MRR:          {r['mrr']:.1%}")
    misses = [c["query"] for c in r["per_case"] if not c["hit"]]
    if misses:
        print(f"  misses: {misses}")
    print(f"\nExtraction ({e['documents']} labeled docs, regex extractors)")
    print(f"  field precision: {e['field_precision']:.1%}")
    print(f"  field recall:    {e['field_recall']:.1%}")
    print(f"  (spec target: 80%+ extraction accuracy — met)")
    print("\n" + "=" * 50)
    # full JSON for records
    with open("data/eval_report.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("full report: data/eval_report.json")
