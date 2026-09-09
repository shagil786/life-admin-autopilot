"""Semantic-ish chunking: paragraphs first, char-window fallback with overlap.

Per RAG best practice: chunk on natural boundaries (paragraphs), keep
chunks small for Q&A recall, add overlap when a paragraph must be split,
and store citation metadata (source, position, doc type).
"""
from typing import Optional


def chunk_document(
    text: str,
    source: str,
    doc_type: Optional[str] = None,
    max_chars: int = 400,
    overlap: int = 100,
) -> list:
    """Split a document into citable chunks.

    Strategy: split on paragraph boundaries; paragraphs longer than
    max_chars are split on sentence-ish boundaries with overlap.
    """
    chunks = []
    index = 0

    def emit(piece: str):
        nonlocal index
        piece = piece.strip()
        if piece:
            chunks.append({
                "id": f"{source}#{index}",
                "text": piece,
                "source": source,
                "doc_type": doc_type,
                "index": index,
            })
            index += 1

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for para in paragraphs:
        if len(para) <= max_chars:
            emit(para)
            continue
        # split long paragraph with overlap
        start = 0
        while start < len(para):
            end = min(start + max_chars, len(para))
            # try to cut at a sentence/space boundary, not mid-word
            if end < len(para):
                cut = max(para.rfind(". ", start, end),
                          para.rfind(" ", start, end))
                if cut > start:
                    end = cut + 1
            emit(para[start:end])
            if end >= len(para):
                break
            start = end - overlap
    return chunks


def chunk_documents(docs: list) -> list:
    """Chunk a list of parsed documents: [{content, source, type}, ...]."""
    all_chunks = []
    for doc in docs:
        all_chunks.extend(
            chunk_document(doc["content"], source=doc["source"],
                           doc_type=doc.get("type"))
        )
    return all_chunks
