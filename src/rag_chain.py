"""
RAG chain: retrieves relevant chunks and generates answers.
Supports OpenAI (paid) and HuggingFace Inference API (free tier).
"""
from typing import List, Tuple, Dict, Any, Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from src.vector_store import similarity_search

RAG_PROMPT = ChatPromptTemplate.from_template(
    """You are a helpful assistant that answers questions based strictly on the provided context.
If the answer is not found in the context, say "I couldn't find relevant information in the document."
Do not make up information beyond what is provided.

Context:
{context}

Question: {question}

Answer:"""
)

# HuggingFace models available via free Inference API
HF_MODELS = [
    "mistralai/Mistral-7B-Instruct-v0.3",
    "HuggingFaceH4/zephyr-7b-beta",
    "meta-llama/Llama-3.2-3B-Instruct",
]


def format_context(docs: List[Document]) -> str:
    """Concatenate document chunks into a single context string."""
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def _build_llm(
    provider: str,
    model_name: str,
    openai_api_key: Optional[str] = None,
    hf_token: Optional[str] = None,
):
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, api_key=openai_api_key, temperature=0.2)

    # HuggingFace Inference API (free tier)
    from langchain_huggingface import HuggingFaceEndpoint
    return HuggingFaceEndpoint(
        repo_id=model_name,
        huggingfacehub_api_token=hf_token,
        temperature=0.2,
        max_new_tokens=512,
    )


def answer_question(
    vector_store: FAISS,
    question: str,
    provider: str = "openai",
    model_name: str = "gpt-4o-mini",
    openai_api_key: Optional[str] = None,
    hf_token: Optional[str] = None,
    k: int = 4,
) -> Dict[str, Any]:
    """
    Retrieve relevant chunks and generate an answer.

    Returns a dict with:
        - answer (str): the LLM response
        - sources (list): list of (Document, score) tuples used as context
    """
    results: List[Tuple[Document, float]] = similarity_search(vector_store, question, k=k)
    source_docs = [doc for doc, _score in results]

    llm = _build_llm(provider, model_name, openai_api_key, hf_token)

    chain = (
        {
            "context": lambda _: format_context(source_docs),
            "question": RunnablePassthrough(),
        }
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )

    answer = chain.invoke(question)

    return {
        "answer": answer,
        "sources": results,
    }
