"""
Qdrant vector store — multi-document edition.
- Each ingested doc is tagged with a unique doc_id.
- All docs share one Qdrant collection; re-indexed on each add/remove.
- Falls back to in-memory Qdrant when QDRANT_URL is not set.
"""
import os
import uuid
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings

COLLECTION_NAME = "askmydoc"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_store = None
_client = None
_all_chunks: List[Document] = []
_docs_registry: Dict[str, Any] = {}  # doc_id -> metadata


def _get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _rebuild() -> None:
    """Rebuild Qdrant collection from _all_chunks."""
    global _store, _client
    from qdrant_client import QdrantClient
    from langchain_qdrant import QdrantVectorStore

    if not _all_chunks:
        _store = None
        return

    qdrant_url = os.getenv("QDRANT_URL", "")
    embeddings = _get_embeddings()

    if qdrant_url:
        _client = QdrantClient(url=qdrant_url)
    else:
        _client = QdrantClient(":memory:")

    try:
        _client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    _store = QdrantVectorStore.from_documents(
        _all_chunks,
        embeddings,
        client=_client,
        collection_name=COLLECTION_NAME,
    )


def add_doc(chunks: List[Document], name: str, strategy: str, pages: int) -> str:
    """Ingest a new document; returns its doc_id."""
    global _all_chunks
    doc_id = str(uuid.uuid4())
    for chunk in chunks:
        chunk.metadata["doc_id"] = doc_id
        chunk.metadata["doc_name"] = name
    _all_chunks.extend(chunks)
    _docs_registry[doc_id] = {
        "id": doc_id,
        "name": name,
        "strategy": strategy,
        "pages": pages,
        "chunks": len(chunks),
    }
    _rebuild()
    return doc_id


def remove_doc(doc_id: str) -> bool:
    """Remove a document and rebuild the collection."""
    global _all_chunks
    if doc_id not in _docs_registry:
        return False
    _all_chunks = [c for c in _all_chunks if c.metadata.get("doc_id") != doc_id]
    del _docs_registry[doc_id]
    _rebuild()
    return True


def get_store():
    return _store


def get_docs() -> List[Dict[str, Any]]:
    return list(_docs_registry.values())


# legacy alias kept for compatibility
def build_store(chunks: List[Document]):
    return add_doc(chunks, "document", "recursive", 0)


def clear_store():
    global _store, _client, _all_chunks
    _all_chunks.clear()
    _docs_registry.clear()
    if _client:
        try:
            _client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
    _store = None
