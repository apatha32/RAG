"""
RAG chain: retrieves relevant chunks and generates answers via OpenAI LLM.
"""
from typing import List, Tuple, Dict, Any

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
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


def format_context(docs: List[Document]) -> str:
    """Concatenate document chunks into a single context string."""
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def answer_question(
    vector_store: FAISS,
    question: str,
    openai_api_key: str,
    model_name: str = "gpt-4o-mini",
    k: int = 4,
) -> Dict[str, Any]:
    """
    Retrieve relevant chunks and generate an answer.

    Returns a dict with:
        - answer (str): the LLM response
        - sources (list): list of (Document, score) tuples used as context
    """
    # Retrieve top-k chunks with similarity scores
    results: List[Tuple[Document, float]] = similarity_search(
        vector_store, question, k=k
    )
    source_docs = [doc for doc, _score in results]

    llm = ChatOpenAI(
        model=model_name,
        api_key=openai_api_key,
        temperature=0.2,
    )

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
        "sources": results,  # [(Document, score), ...]
    }
