"""Extraction quality evaluation: field-level precision and recall.

For each labeled case, run the matching regex extractor and compare
fields against ground truth. (LLM fallback is evaluated separately —
it costs gateway calls; regex is deterministic and free.)
"""
from src.eval_harness import datasets
from src.extraction.receipt_extractor import ReceiptExtractor
from src.extraction.subscription_extractor import SubscriptionExtractor
from src.extraction.warranty_extractor import WarrantyExtractor
from src.ingestion.base import Document


def _extractor_for(doc_type: str):
    return {
        "receipt": ReceiptExtractor,
        "subscription": SubscriptionExtractor,
        "warranty": WarrantyExtractor,
    }.get(doc_type)


def evaluate_extraction() -> dict:
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    per_case = []

    for case in datasets.EXTRACTION_CASES:
        doc = Document(type=case["doc_type"], content=case["text"],
                       source="eval")
        extractor_cls = _extractor_for(case["doc_type"])
        extracted = extractor_cls().extract(doc) if extractor_cls else {}

        expected = case["expected"]
        case_tp = case_fp = case_fn = 0
        fields = {}
        for key, want in expected.items():
            got = extracted.get(key)
            ok = got == want
            fields[key] = {"expected": want, "got": got, "ok": ok}
            if ok:
                true_positives += 1
                case_tp += 1
            else:
                false_negatives += 1
                case_fn += 1
        # false positives: extracted keys that aren't in expected and
        # aren't metadata
        for key, got in extracted.items():
            if key in ("source",) or key in expected:
                continue
            if got is not None:
                false_positives += 1
                case_fp += 1
        per_case.append({"text": case["text"][:40], "fields": fields,
                         "tp": case_tp, "fp": case_fp, "fn": case_fn})

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) else 0.0
    )
    return {
        "field_precision": round(precision, 3),
        "field_recall": round(recall, 3),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "documents": len(datasets.EXTRACTION_CASES),
        "per_case": per_case,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(evaluate_extraction(), indent=2, default=str))
