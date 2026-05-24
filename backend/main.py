"""
AskMyDoc — FastAPI backend v2
New: session memory, multi-doc, model selector, rate limiting, evaluation endpoint.
"""
import json
import os
import uuid
from collections import defaultdict
from typing import List, Optional

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.rag.loader import load_pdf, load_url
from src.rag.chunkers import get_chunker
from src.rag import vector_store as vs
from src.agent.graph import create_agent

load_dotenv()

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour"])
app = FastAPI(title="AskMyDoc API", version="3.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Session store (in-memory; swap for Redis in production) ───────────────────
_sessions: dict[str, list] = defaultdict(list)
MAX_HISTORY = 20  # messages kept per session


# ── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None
    hf_token: Optional[str] = None


class EvalRequest(BaseModel):
    question: str
    answer: str
    contexts: List[str] = []


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    docs = vs.get_docs()
    return {
        "status": "ok",
        "docs_loaded": len(docs) > 0,
        "doc_count": len(docs),
    }


@app.get("/documents")
def list_documents():
    return {"documents": vs.get_docs()}


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    if not vs.remove_doc(doc_id):
        raise HTTPException(404, f"Document '{doc_id}' not found.")
    return {"message": "Document removed."}


@app.post("/ingest")
async def ingest(
    strategy: str = Form("recursive"),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(150),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    if not file and not url:
        raise HTTPException(400, "Provide either a file upload or a URL.")

    if file:
        raw = await file.read()
        docs = load_pdf(raw, file.filename)
        name = file.filename or "upload"
    else:
        docs = load_url(url)
        name = url or "web"

    if not docs:
        raise HTTPException(422, "Could not extract any text from the source.")

    chunker = get_chunker(strategy, chunk_size, chunk_overlap)
    chunks = chunker.split(docs)

    if not chunks:
        raise HTTPException(422, "Chunking produced no chunks.")

    doc_id = vs.add_doc(chunks, name=name, strategy=strategy, pages=len(docs))

    return {
        "message": f"Indexed {len(chunks)} chunks using '{strategy}' strategy.",
        "doc_id": doc_id,
        "chunks": len(chunks),
        "strategy": strategy,
        "pages": len(docs),
    }


@app.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest):
    store = vs.get_store()
    openai_key = req.openai_api_key or os.getenv("OPENAI_API_KEY")
    hf_token = req.hf_token or os.getenv("HF_TOKEN")

    if req.provider == "openai" and not openai_key:
        raise HTTPException(400, "OpenAI API key is required.")
    if req.provider == "huggingface" and not hf_token:
        raise HTTPException(400, "HuggingFace token is required.")

    # Session memory
    session_id = req.session_id or str(uuid.uuid4())
    history = _sessions[session_id]

    # Convert stored history to LangChain messages
    lc_history = []
    for h in history:
        if h["role"] == "user":
            lc_history.append(HumanMessage(content=h["content"]))
        else:
            lc_history.append(AIMessage(content=h["content"]))
    lc_history.append(HumanMessage(content=req.message))

    agent = create_agent(
        vector_store=store,
        provider=req.provider,
        model=req.model,
        openai_api_key=openai_key,
        hf_token=hf_token,
    )

    async def event_stream():
        full_response = ""
        try:
            async for event in agent.astream_events(
                {"messages": lc_history},
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        full_response += chunk
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

                elif kind == "on_tool_start":
                    payload = {
                        "type": "tool_start",
                        "name": event.get("name", ""),
                        "input": str(event["data"].get("input", ""))[:400],
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                elif kind == "on_tool_end":
                    payload = {
                        "type": "tool_end",
                        "name": event.get("name", ""),
                        "output": str(event["data"].get("output", ""))[:600],
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

            # Persist to session
            history.append({"role": "user", "content": req.message})
            history.append({"role": "assistant", "content": full_response})
            _sessions[session_id] = history[-MAX_HISTORY:]

            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/evaluate")
async def evaluate(req: EvalRequest):
    """Embedding-based RAG quality metrics (no external LLM needed)."""
    from langchain_community.embeddings import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )

    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    q = np.array(embeddings.embed_query(req.question))
    a = np.array(embeddings.embed_query(req.answer))
    ctx_text = " ".join(req.contexts) if req.contexts else req.answer
    c = np.array(embeddings.embed_query(ctx_text))

    return {
        "answer_relevancy": round(cosine(q, a), 3),
        "faithfulness": round(cosine(a, c), 3),
        "context_recall": round(cosine(q, c), 3),
    }


@app.delete("/collection")
def clear_collection():
    vs.clear_store()
    _sessions.clear()
    return {"message": "Vector store and sessions cleared."}
