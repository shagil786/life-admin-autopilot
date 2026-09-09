"""RAG package: local hybrid retrieval over ingested documents."""
from src.rag.chunker import chunk_documents
from src.rag.index import DocumentIndex
from src.rag.service import RagService, HALLUCINATION_GUARD

__all__ = ["chunk_documents", "DocumentIndex", "RagService",
           "HALLUCINATION_GUARD"]
