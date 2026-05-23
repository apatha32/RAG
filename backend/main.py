"""
AskMyDoc — FastAPI backend
Endpoints:
  GET  /health          — liveness check
  POST /ingest          — upload PDF or URL, choose chunking strategy
  POST /chat            — SSE streaming chat with LangGraph agent
  DELETE /collection    — clear the vector store
"""
import json
import os
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from src.rag.loader import load_pdf, load_url
from src.rag.chunkers import get_chunker
from src.rag import vector_store as vs
from src.agent.graph import create_agent

load_dotenv()

app = FastAPI(title="AskMyDoc API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    provider: str = "openai"
    openai_api_key: Optional[str] = None
    hf_token: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "docs_loaded": vs.get_store() is not None,
    }


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

    # Load
    if file:
        raw = await file.read()
        docs = load_pdf(raw, file.filename)
    else:
        docs = load_url(url)

    if not docs:
        raise HTTPException(422, "Could not extract any text from the source.")

    # Chunk
    chunker = get_chunker(strategy, chunk_size, chunk_overlap)
    chunks = chunker.split(docs)

    if not chunks:
        raise HTTPException(422, "Chunking produced no chunks. Try a different strategy or larger chunk size.")

    # Index
    vs.build_store(chunks)

    return {
        "message": f"Indexed {len(chunks)} chunks using '{strategy}' strategy.",
        "chunks": len(chunks),
        "strategy": strategy,
        "pages": len(docs),
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    store = vs.get_store()

    # Resolve API keys: request body → env fallback
    openai_key = req.openai_api_key or os.getenv("OPENAI_API_KEY")
    hf_token = req.hf_token or os.getenv("HF_TOKEN")

    if req.provider == "openai" and not openai_key:
        raise HTTPException(400, "OpenAI API key is required for the OpenAI provider.")
    if req.provider == "huggingface" and not hf_token:
        raise HTTPException(400, "HuggingFace token is required for the HuggingFace provider.")

    agent = create_agent(
        vector_store=store,
        provider=req.provider,
        openai_api_key=openai_key,
        hf_token=hf_token,
    )

    async def event_stream():
        try:
            async for event in agent.astream_events(
                {"messages": [{"role": "user", "content": req.message}]},
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if chunk:
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

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.delete("/collection")
def clear_collection():
    vs.clear_store()
    return {"message": "Vector store cleared."}
