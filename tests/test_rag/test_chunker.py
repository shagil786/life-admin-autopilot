"""Tests for document chunking."""
from src.rag.chunker import chunk_document


def test_chunks_by_paragraph():
    text = "Paragraph one about Netflix.\n\nParagraph two about gym."
    chunks = chunk_document(text, source="a.txt")
    assert len(chunks) >= 2
    assert "Netflix" in chunks[0]["text"]
    assert "gym" in chunks[1]["text"]


def test_chunk_metadata():
    text = "Some content here."
    chunks = chunk_document(text, source="receipt.txt", doc_type="receipt")
    assert chunks[0]["source"] == "receipt.txt"
    assert chunks[0]["doc_type"] == "receipt"
    assert chunks[0]["index"] == 0


def test_small_doc_single_chunk():
    text = "One line only."
    chunks = chunk_document(text, source="a.txt")
    assert len(chunks) == 1


def test_long_paragraph_split_with_overlap():
    # A single huge paragraph must be split, with overlap between pieces
    para = "word " * 400  # ~2000 chars
    chunks = chunk_document(para, source="a.txt", max_chars=500, overlap=100)
    assert len(chunks) > 1
    # overlap: end of chunk 0 reappears at start of chunk 1
    assert chunks[1]["text"][:50].strip() in para
    # second chunk should start with the tail of the first
    assert chunks[0]["text"][-50:].strip() in chunks[1]["text"]


def test_strips_empty_chunks():
    text = "Real text.\n\n\n\n   \n\nMore."
    chunks = chunk_document(text, source="a.txt")
    assert all(c["text"].strip() for c in chunks)


def test_citation_id():
    text = "hello"
    chunks = chunk_document(text, source="folder/receipt.txt")
    assert chunks[0]["id"] == "folder/receipt.txt#0"
