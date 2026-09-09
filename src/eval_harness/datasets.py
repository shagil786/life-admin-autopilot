"""Labeled evaluation datasets.

RETRIEVAL_CASES: queries a user would actually ask, with the document
file (name contains) that should be retrieved.

EXTRACTION_CASES: document text -> expected fields, ground-truthed by
hand. Used to measure extraction precision/recall (spec target: 80%+).
"""

RETRIEVAL_CASES = [
    {"query": "When does Netflix renew?",
     "expected_source": "netflix"},
    {"query": "how much are the headphones",
     "expected_source": "headphones"},
    {"query": "gym membership renewal date",
     "expected_source": "gym"},
    {"query": "laptop warranty expiration",
     "expected_source": "laptop"},
    {"query": "what did Spotify email say",
     "expected_source": "spotify"},
    {"query": "Amazon purchase return",
     "expected_source": "headphones"},   # Amazon receipt is the headphones one
    {"query": "ACME furniture invoice total",
     "expected_source": "messy_receipt"},
    {"query": "vacuum cleaner Dyson warranty",
     "expected_source": "vacuum"},
    {"query": "what tasks are noise or irrelevant",
     "expected_source": "noise"},
    {"query": "monthly subscription cost",
     "expected_source": "netflix"},
]


EXTRACTION_CASES = [
    {
        "text": "Amazon purchase $49.99 on 2024-01-15",
        "doc_type": "receipt",
        "expected": {"vendor": "Amazon", "amount": 49.99, "date": "2024-01-15"},
    },
    {
        "text": "Netflix subscription $15.99/month, renews 2025-01-15",
        "doc_type": "subscription",
        "expected": {"name": "Netflix", "amount": 15.99,
                     "billing_cycle": "monthly", "next_billing_date": "2025-01-15"},
    },
    {
        "text": "Costco membership $60/year renews 2025-06-01",
        "doc_type": "subscription",
        "expected": {"name": "Costco", "amount": 60.0, "billing_cycle": "yearly",
                     "next_billing_date": "2025-06-01"},
    },
    {
        "text": "Dell XPS 15 purchased 2024-11-08, 2 year warranty",
        "doc_type": "warranty",
        "expected": {"product": "Dell XPS 15", "warranty_years": 2,
                     "purchase_date": "2024-11-08", "warranty_expires": "2026-11-08"},
    },
    {
        "text": "Sony WH-1000XM5 purchased 2024-06-01, 2 year warranty",
        "doc_type": "warranty",
        "expected": {"product": "Sony WH-1000XM5", "warranty_years": 2,
                     "purchase_date": "2024-06-01", "warranty_expires": "2026-06-01"},
    },
    {
        "text": "Planet Fitness membership $24.99/month, renews 2026-10-24",
        "doc_type": "subscription",
        "expected": {"name": "Planet Fitness", "amount": 24.99,
                     "billing_cycle": "monthly", "next_billing_date": "2026-10-24"},
    },
]
