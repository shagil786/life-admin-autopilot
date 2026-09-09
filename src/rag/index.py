"""Local hybrid retrieval index.

Two legs, combined (per hybrid-retrieval best practice):
1. BM25-style keyword scoring — exact term matching, robust for ids,
   amounts, dates ("Netflix", "$15.99", "2026-09-12")
2. TF-IDF cosine similarity — semantic-ish recall across wording

No external service: the corpus is personal documents (dozens, not
millions), so a local inverted index keeps everything on-device —
which is a core promise of Life Admin Autopilot.
"""
import math
import re
from collections import Counter
from typing import Optional

_TOKEN_RE = re.compile(r"[a-z0-9$%.-]+")

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is",
    "was", "my", "me", "i", "it", "at", "by", "with", "this", "that",
}


def tokenize(text: str) -> list:
    tokens = _TOKEN_RE.findall(text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


class DocumentIndex:
    """In-memory hybrid search index over chunks."""

    def __init__(self):
        self._chunks = {}          # id -> chunk dict
        self._doc_freq = Counter()  # token -> number of chunks containing it
        self._token_counts = {}     # chunk id -> Counter of tokens

    # -- indexing ----------------------------------------------------------

    def add_chunks(self, chunks: list):
        for chunk in chunks:
            cid = chunk["id"]
            self._chunks[cid] = chunk
            tokens = tokenize(chunk["text"])
            counts = Counter(tokens)
            self._token_counts[cid] = counts
            for token in counts:
                self._doc_freq[token] += 1

    @property
    def size(self) -> int:
        return len(self._chunks)

    # -- retrieval ---------------------------------------------------------

    def search(self, query: str, doc_type: Optional[str] = None,
               top_k: int = 5) -> list:
        """Hybrid search. Returns [{chunk, score, citation}] best-first."""
        if not self._chunks:
            return []
        candidates = [
            c for c in self._chunks.values()
            if doc_type is None or c.get("doc_type") == doc_type
        ]
        if not candidates:
            return []
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        scored = []
        n = len(self._chunks)
        avg_len = (
            sum(len(t) for t in self._token_counts.values()) / n
            if n else 0
        ) or 1

        for chunk in candidates:
            cid = chunk["id"]
            counts = self._token_counts.get(cid, Counter())
            bm25 = self._bm25(q_tokens, counts, n, avg_len)
            cosine = self._cosine(q_tokens, counts)
            score = 0.6 * bm25 + 0.4 * cosine
            if score > 0:
                scored.append({
                    "chunk": chunk,
                    "score": round(score, 4),
                    "citation": cid,
                })

        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]

    def _bm25(self, q_tokens, counts, n, avg_len, k1=1.5, b=0.75) -> float:
        """Standard BM25 score of a query against one chunk."""
        score = 0.0
        doc_len = sum(counts.values()) or 1
        for term in set(q_tokens):
            tf = counts.get(term, 0)
            if tf == 0:
                continue
            df = self._doc_freq.get(term, 0)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            norm = tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_len / avg_len))
            score += idf * norm
        return score

    def _cosine(self, q_tokens, counts) -> float:
        """TF-IDF cosine similarity between query and chunk."""
        q_counts = Counter(q_tokens)
        n = max(len(self._chunks), 1)
        common = set(q_counts) & set(counts)
        if not common:
            return 0.0
        def weight(term, count):
            idf = math.log(1 + n / (self._doc_freq.get(term, 0) + 1))
            return count * idf
        dot = sum(weight(t, q_counts[t]) * weight(t, counts[t]) for t in common)
        q_mag = math.sqrt(sum(w ** 2 for w in (weight(t, c) for t, c in q_counts.items())))
        d_mag = math.sqrt(sum(w ** 2 for w in (weight(t, c) for t, c in counts.items())))
        if q_mag == 0 or d_mag == 0:
            return 0.0
        return dot / (q_mag * d_mag)
