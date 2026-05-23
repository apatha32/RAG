"""
Qdrant vector store wrapper.
Uses in-memory Qdrant when QDRANT_URL is not set (local dev without Docker).
"""
import os
from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings

COLLECTION_NAME = "askmydoc"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_store = None
_client = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def build_store(chunks: List[Document]):
    global _store, _client
    from qdrant_client import QdrantClient
    from langchain_qdrant import QdrantVectorStore

    qdrant_url = os.getenv("QDRANT_URL", "")
    embeddings = _get_embeddings()

    if qdrant_url:
        _client = QdrantClient(url=qdrant_url)
    else:
        _client = QdrantClient(":memory:")

    # Drop existing collection to allow re-ingestion
    try:
        _client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    _store = QdrantVectorStore.from_documents(
        chunks,
        embeddings,
        client=_client,
        collection_name=COLLECTION_NAME,
    )
    return _store


def get_store():
    return _store


def clear_store():
    global _store, _client
    if _client:
        try:
            _client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
    _store = None
