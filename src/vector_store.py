"""
Vector store: builds and queries a FAISS index using HuggingFace embeddings.
No API key required for embeddings.
"""
from typing import List, Tuple
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# Lightweight, fast embedding model (~80MB, runs on CPU)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return a HuggingFace embedding model (cached after first load)."""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def build_vector_store(chunks: List[Document]) -> FAISS:
    """Embed chunks and build a FAISS vector store."""
    embeddings = get_embeddings()
    vector_store = FAISS.from_documents(chunks, embeddings)
    return vector_store


def similarity_search(
    vector_store: FAISS,
    query: str,
    k: int = 4,
) -> List[Tuple[Document, float]]:
    """Return top-k (document, score) pairs for the given query."""
    results = vector_store.similarity_search_with_score(query, k=k)
    return results
