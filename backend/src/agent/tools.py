"""
Agent tools:
  - rag_search   : hybrid BM25 + dense retrieval from ingested document
  - web_search   : Tavily API (requires TAVILY_API_KEY)
"""
import os
from langchain_core.tools import tool
from langchain_core.documents import Document
from typing import List


def make_rag_tool(vector_store):
    @tool
    def rag_search(query: str) -> str:
        """
        Search the uploaded document for information relevant to the query.
        Always use this first when answering questions about the document.
        """
        if vector_store is None:
            return "No document has been ingested yet. Ask the user to upload a PDF or URL."

        # Dense retrieval
        dense_docs: List[Document] = vector_store.similarity_search(query, k=6)

        # BM25 sparse retrieval over the same collection
        try:
            from langchain_community.retrievers import BM25Retriever
            from langchain.retrievers import EnsembleRetriever

            all_docs = vector_store.similarity_search("", k=200)  # fetch all
            if len(all_docs) > 0:
                bm25 = BM25Retriever.from_documents(all_docs, k=6)
                dense_retriever = vector_store.as_retriever(search_kwargs={"k": 6})
                hybrid = EnsembleRetriever(
                    retrievers=[bm25, dense_retriever], weights=[0.4, 0.6]
                )
                docs = hybrid.invoke(query)[:6]
            else:
                docs = dense_docs
        except Exception:
            docs = dense_docs

        if not docs:
            return "No relevant content found in the document."

        results = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "document")
            page = doc.metadata.get("page", "")
            strategy = doc.metadata.get("chunking_strategy", "")
            header = f"[Chunk {i} | {source}{f' p.{int(page)+1}' if page != '' else ''} | {strategy}]"
            results.append(f"{header}\n{doc.page_content}")

        return "\n\n---\n\n".join(results)

    return rag_search


def make_web_search_tool():
    @tool
    def web_search(query: str) -> str:
        """
        Search the web for real-time or general knowledge not found in the document.
        Use this when the document doesn't contain the answer.
        """
        api_key = os.getenv("TAVILY_API_KEY", "")
        if not api_key:
            return "Web search is unavailable (TAVILY_API_KEY not configured)."
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            response = client.search(query, max_results=4)
            results = []
            for r in response.get("results", []):
                results.append(f"**{r['title']}** ({r['url']})\n{r['content']}")
            return "\n\n---\n\n".join(results) if results else "No results found."
        except Exception as e:
            return f"Web search failed: {e}"

    return web_search
