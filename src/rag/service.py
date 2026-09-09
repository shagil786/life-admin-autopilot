"""RAG service: ingest documents into the index, query with citations.

Local-first: everything stays in memory / on disk. No external
embedding service — hybrid BM25 + TF-IDF retrieval (see index.py).
"""
from pathlib import Path
from typing import Optional

from src.ingestion.pdf_parser import PDFParser
from src.ingestion.text_parser import TextParser
from src.ingestion.email_parser import EmailParser
from src.rag.chunker import chunk_documents
from src.rag.index import DocumentIndex

HALLUCINATION_GUARD = (
    "Answer ONLY from the provided context chunks. If the context does "
    "not contain the answer, say you don't know. Cite the chunk id "
    "(like file.txt#0) for every claim."
)


class RagService:
    def __init__(self, samples_dir: str = "data/samples"):
        self._dir = Path(samples_dir)
        self.index = DocumentIndex()
        self._parsers = {
            ".pdf": PDFParser(), ".txt": TextParser(),
            ".md": TextParser(), ".eml": EmailParser(),
        }

    def ingest(self) -> int:
        """Parse + classify + chunk + index every supported doc."""
        if not self._dir.exists():
            return 0
        docs = []
        for path in sorted(self._dir.iterdir()):
            parser = self._parsers.get(path.suffix.lower())
            if not parser:
                continue
            doc = parser.parse(str(path))
            docs.append({
                "content": doc.content,
                "source": str(path),
                "type": self._classify(doc),
            })
        chunks = chunk_documents(docs)
        self.index = DocumentIndex()  # fresh index on re-ingest
        self.index.add_chunks(chunks)
        return len(chunks)

    def _classify(self, doc) -> str:
        """Best-effort doc type from extractor signals."""
        from src.extraction.subscription_extractor import SubscriptionExtractor
        from src.extraction.warranty_extractor import WarrantyExtractor

        if SubscriptionExtractor().extract(doc).get("next_billing_date"):
            return "subscription"
        if WarrantyExtractor().extract(doc).get("warranty_expires"):
            return "warranty"
        return doc.type  # parser default (receipt/email/text)

    def query(self, query: str, doc_type: Optional[str] = None,
              top_k: int = 5) -> list:
        """Hybrid retrieval. Returns [{chunk, score, citation}]."""
        return self.index.search(query, doc_type=doc_type, top_k=top_k)

    def build_context(self, query: str, max_chars: int = 3000,
                      doc_type: Optional[str] = None) -> str:
        """Construct a cited, relevance-ordered context for an LLM.

        Per best practice: order by relevance, include citations,
        respect a context budget, stop when full.
        """
        results = self.query(query, doc_type=doc_type, top_k=10)
        parts = []
        budget = max_chars
        for r in results:
            entry = f"[{r['citation']}] {r['chunk']['text']}"
            if budget - len(entry) < 0:
                break
            parts.append(entry)
            budget -= len(entry) + 1
        return "\n\n".join(parts)
