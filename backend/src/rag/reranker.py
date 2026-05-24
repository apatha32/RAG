"""
Cross-encoder re-ranker using ms-marco-MiniLM-L-6-v2.
Downloads ~80 MB on first use; cached afterwards.
"""
from typing import List
from langchain_core.documents import Document

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
    return _model


def rerank(query: str, docs: List[Document], top_k: int = 6) -> List[Document]:
    """Re-rank documents by cross-encoder score; falls back gracefully."""
    if len(docs) <= top_k:
        return docs
    try:
        model = _get_model()
        pairs = [(query, doc.page_content[:512]) for doc in docs]
        scores = model.predict(pairs)
        ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
        return [doc for _, doc in ranked[:top_k]]
    except Exception:
        return docs[:top_k]
