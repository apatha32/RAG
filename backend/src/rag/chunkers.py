"""
Four chunking strategies:
  1. fixed      — simple fixed-size character splits
  2. recursive  — recursive character splitting (hierarchy-aware)
  3. semantic   — groups sentences by semantic similarity
  4. sentence_window — each chunk is a sentence + surrounding window
"""
import re
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter


class FixedSizeChunker:
    """Split on fixed character count with no structure awareness."""
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        self.splitter = CharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=" ",
        )

    def split(self, docs: List[Document]) -> List[Document]:
        chunks = self.splitter.split_documents(docs)
        for c in chunks:
            c.metadata["chunking_strategy"] = "fixed"
        return chunks


class RecursiveChunker:
    """Recursively split on paragraph → sentence → word boundaries."""
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split(self, docs: List[Document]) -> List[Document]:
        chunks = self.splitter.split_documents(docs)
        for c in chunks:
            c.metadata["chunking_strategy"] = "recursive"
        return chunks


class SemanticChunker:
    """Group sentences by embedding similarity — keeps related ideas together."""
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 0):
        self.chunk_size = chunk_size

    def split(self, docs: List[Document]) -> List[Document]:
        try:
            from langchain_experimental.text_splitter import SemanticChunker
            from langchain_community.embeddings import HuggingFaceEmbeddings
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
            )
            splitter = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
            chunks = splitter.split_documents(docs)
        except Exception:
            # Fallback to recursive if experimental not available
            chunks = RecursiveChunker(self.chunk_size).split(docs)
        for c in chunks:
            c.metadata["chunking_strategy"] = "semantic"
        return chunks


class SentenceWindowChunker:
    """
    Split by sentence; each chunk contains the target sentence padded
    with `window` surrounding sentences for richer context.
    """
    def __init__(self, window: int = 2, **_):
        self.window = window

    def _sentence_split(self, text: str) -> List[str]:
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    def split(self, docs: List[Document]) -> List[Document]:
        chunks: List[Document] = []
        for doc in docs:
            sentences = self._sentence_split(doc.page_content)
            for i, sentence in enumerate(sentences):
                start = max(0, i - self.window)
                end = min(len(sentences), i + self.window + 1)
                window_text = " ".join(sentences[start:end])
                chunks.append(Document(
                    page_content=window_text,
                    metadata={
                        **doc.metadata,
                        "chunking_strategy": "sentence_window",
                        "core_sentence": sentence,
                        "window_size": self.window,
                    },
                ))
        return chunks


_STRATEGIES = {
    "fixed": FixedSizeChunker,
    "recursive": RecursiveChunker,
    "semantic": SemanticChunker,
    "sentence_window": SentenceWindowChunker,
}


def get_chunker(strategy: str, chunk_size: int = 1000, chunk_overlap: int = 150):
    cls = _STRATEGIES.get(strategy, RecursiveChunker)
    return cls(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
