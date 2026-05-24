"""
Agent tools:
  - rag_search : HyDE query rewriting → hybrid BM25 + dense retrieval → cross-encoder re-rank
  - web_search : Tavily API (requires TAVILY_API_KEY)
"""
import os
from langchain_core.tools import tool
from langchain_core.documents import Document
from typing import List


def _hyde_rewrite(query: str) -> str:
    """
    HyDE (Hypothetical Document Embeddings): generate a short hypothetical answer
    to the query, then use THAT as the retrieval query. Dramatically improves
    recall for vague or short questions.
    Falls back to the original query if an LLM is unavailable.
    """
    try:
        from langchain_openai import ChatOpenAI
        import os
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return query
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=api_key, max_tokens=120)
        prompt = (
            "Write a concise 2-3 sentence passage that would directly answer the following question. "
            "Do not include the question itself.\n\nQuestion: " + query
        )
        response = llm.invoke(prompt)
        hypothetical = response.content.strip()
        return hypothetical if hypothetical else query
    except Exception:
        return query


def make_rag_tool(vector_store):
    @tool
    def rag_search(query: str) -> str:
        """
        Search the uploaded document(s) for information relevant to the query.
        Always use this first when answering questions about the document.
        """
        if vector_store is None:
            return "No document has been ingested yet. Ask the user to upload a PDF or URL."

        # Step 1: HyDE — rewrite query into a hypothetical answer for better retrieval
        retrieval_query = _hyde_rewrite(query)

        # Step 2: retrieve larger candidate pool (hybrid BM25 + dense)
        dense_docs: List[Document] = vector_store.similarity_search(retrieval_query, k=12)
        # Step 3: hybrid BM25 + dense retrieval
        try:
            from langchain_community.retrievers import BM25Retriever
            from langchain.retrievers import EnsembleRetriever

            all_docs = vector_store.similarity_search("", k=500)
            if all_docs:
                bm25 = BM25Retriever.from_documents(all_docs, k=12)
                dense_ret = vector_store.as_retriever(search_kwargs={"k": 12})
                hybrid = EnsembleRetriever(
                    retrievers=[bm25, dense_ret], weights=[0.4, 0.6]
                )
                candidates = hybrid.invoke(retrieval_query)
            else:
                candidates = dense_docs
        except Exception:
            candidates = dense_docs

        # Step 4: cross-encoder re-rank against the ORIGINAL query → top 6
        try:
            from src.rag.reranker import rerank
            docs = rerank(query, candidates, top_k=6)
        except Exception:
            docs = candidates[:6]

        if not docs:
            return "No relevant content found in the document."

        results = []
        for i, doc in enumerate(docs, 1):
            name = doc.metadata.get("doc_name", doc.metadata.get("source", "document"))
            page = doc.metadata.get("page", "")
            strategy = doc.metadata.get("chunking_strategy", "")
            page_str = f" p.{int(page)+1}" if page != "" else ""
            header = f"[Chunk {i} | {name}{page_str} | {strategy}]"
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
