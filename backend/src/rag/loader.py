"""Document loader: supports PDF files and web URLs."""
import tempfile
import os
from typing import List
from langchain_core.documents import Document


def load_pdf(file_bytes: bytes, filename: str) -> List[Document]:
    from langchain_community.document_loaders import PyPDFLoader
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        loader = PyPDFLoader(tmp_path)
        docs = loader.load()
        for doc in docs:
            doc.metadata["source"] = filename
        return docs
    finally:
        os.unlink(tmp_path)


def load_url(url: str) -> List[Document]:
    from langchain_community.document_loaders import WebBaseLoader
    loader = WebBaseLoader(url)
    docs = loader.load()
    return docs
