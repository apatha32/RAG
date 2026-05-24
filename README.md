---
title: AskMyDoc
emoji: 🤖
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
license: mit
---

<h1 align="center">AskMyDoc — AI Research Agent</h1>

<p align="center">
  A production-grade <strong>single AI agent with RAG backbone</strong> — upload any document and converse with an autonomous agent that retrieves from your documents and the web in real time.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-15-black?logo=next.js&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/LangGraph-ReAct%20Agent-1C3C3C?logo=langchain&logoColor=white" />
  <img src="https://img.shields.io/badge/Qdrant-Vector%20DB-E85D4A" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" />
</p>

<p align="center">
  <a href="https://ambarish0221-askmydoc.hf.space">
    <img src="https://img.shields.io/badge/Live%20Demo-AskMyDoc-yellow?style=for-the-badge" />
  </a>
  &nbsp;
  <a href="https://huggingface.co/spaces/ambarish0221/AskMyDoc">
    <img src="https://img.shields.io/badge/HuggingFace-Space-orange?style=for-the-badge&logo=huggingface" />
  </a>
  &nbsp;
  <a href="https://github.com/apatha32/RAG-Agent-AskMyDoc">
    <img src="https://img.shields.io/badge/GitHub-RAG--Agent--AskMyDoc-black?style=for-the-badge&logo=github" />
  </a>
</p>

---

## Architecture

```
Browser (Next.js 15 + Tailwind)
        │  SSE stream (tokens + agent steps)
        ▼
FastAPI (port 8000)
  ├── Input guardrails       ← prompt injection detection, length limits
  ├── Session memory (20-turn history per UUID)
  ├── Rate limiting (slowapi, 20/min)
  ├── GET  /health            ← live status
  ├── POST /ingest            ← upload PDF or URL
  ├── GET  /documents         ← list ingested docs
  ├── DELETE /documents/{id}  ← remove single doc
  ├── POST /chat              ← SSE agent stream
  └── POST /evaluate          ← embedding-based metrics
        │
        ▼
 LangGraph ReAct Agent
   ├── rag_search  ─────► HyDE rewrite → Qdrant (BM25 + dense → cross-encoder re-rank top-6)
   │                          └── sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
   │                          └── cross-encoder/ms-marco-MiniLM-L-6-v2
   └── web_search  ─────► Tavily API
        │
        ▼
   LLM (OpenAI: gpt-4o-mini / gpt-4o / gpt-3.5-turbo)
      OR (HuggingFace: Mistral-7B / Zephyr-7B / Llama-3)
```

---

## Project Structure

```
RAG-Agent-AskMyDoc/
├── docker-compose.yml
├── env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                   # FastAPI: all endpoints + session store
│   └── src/
│       ├── rag/
│       │   ├── loader.py         # PDF + URL document loaders
│       │   ├── chunkers.py       # 4 chunking strategies
│       ├── vector_store.py   # Qdrant client + multi-doc registry (multilingual embeddings)
│       │   ├── reranker.py       # Cross-encoder re-ranking
│       │   └── guardrails.py     # Input validation + output quality checks
│       └── agent/
│           ├── tools.py          # rag_search (HyDE + hybrid) + web_search tools
│           └── graph.py          # LangGraph ReAct agent (model selector)
└── frontend/
    ├── Dockerfile
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx              # Layout: health banner + model selector + sidebar
    │   └── globals.css
    └── components/
        ├── ChatWindow.tsx        # SSE consumer + session ID management
        ├── MessageBubble.tsx     # Markdown + citations + eval panel
        ├── DocumentPanel.tsx     # Upload + doc list + per-doc delete
        ├── AgentTrace.tsx        # Collapsible tool call viewer
        ├── SourceCitation.tsx    # [Chunk N | file | strategy] badge parser
        └── EvalPanel.tsx         # answer_relevancy / faithfulness / context_recall bars
```

---

## Quickstart (Docker Compose — recommended)

```bash
git clone https://github.com/apatha32/RAG-Agent-AskMyDoc.git
cd RAG-Agent-AskMyDoc

cp env.example .env
# Edit .env — add OPENAI_API_KEY and/or HF_TOKEN

docker compose up --build
```

Open **http://localhost:3000** — that's it.

---

## Local Development (without Docker)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../env.example .env   # add your keys
uvicorn main:app --reload --port 8000
```

> No Qdrant running? The backend falls back to an **in-memory Qdrant client** automatically.

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Open **http://localhost:3000**.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | For OpenAI models | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `HF_TOKEN` | For HuggingFace models | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| `TAVILY_API_KEY` | Optional — web search | Free tier at [tavily.com](https://tavily.com) |
| `QDRANT_URL` | Set by Docker Compose | Override for external Qdrant |

---

## Tech Stack

**Backend** — Python 3.11, FastAPI, LangGraph, LangChain, Qdrant, sentence-transformers (multilingual MiniLM + cross-encoder), slowapi, Tavily  
**Frontend** — Next.js 15, React 19, Tailwind CSS, TypeScript  
**Infrastructure** — Docker Compose (Qdrant + FastAPI + Next.js)

---

## Key Features

| Feature | Details |
|---|---|
| **HyDE query rewriting** | Before retrieval, the LLM generates a hypothetical answer to the query and retrieves against that — improves recall on short or vague questions |
| **Multilingual embeddings** | `paraphrase-multilingual-MiniLM-L12-v2` supports 50+ languages; same 384-dim space, drop-in replacement |
| **Input guardrails** | Detects prompt injection / jailbreak patterns, rejects oversized inputs, returns 400 with a clear reason |
| **Output guardrails** | Truncates runaway responses, flags hallucination signal phrases |
| **Hybrid retrieval** | BM25 + dense vector search combined via `EnsembleRetriever` |
| **Cross-encoder re-ranking** | Top-12 candidates re-ranked to top-6 via `ms-marco-MiniLM-L-6-v2` |
| **Session memory** | 20-turn conversation history per UUID session |
| **Multi-document support** | Upload and query multiple PDFs/URLs simultaneously |
| **RAG evaluation** | Embedding-based answer relevancy, faithfulness, and context recall scores |
| **Model selector** | Switch between OpenAI (gpt-4o-mini/gpt-4o) and HuggingFace (Mistral/Zephyr/Llama-3) at runtime |

---

## Chunking Strategies

| Strategy | How it works | Best for |
|---|---|---|
| **Recursive** | Splits on `\n\n → \n → . → space` | General documents |
| **Fixed Size** | Fixed character count, `separator=" "` | Tabular / code-heavy docs |
| **Semantic** | Groups sentences by embedding similarity | Dense academic text |
| **Sentence Window** | Sentence + ±2 surrounding sentences | Precise Q&A |

---

## RAG Evaluation Metrics

After each completed answer, click **Evaluate** to get three embedding-based quality scores:

| Metric | Measures |
|---|---|
| **Answer Relevancy** | How well the answer addresses the question |
| **Faithfulness** | How grounded the answer is in the retrieved context |
| **Context Recall** | How well the retrieved context covers the question |

Scores are computed via cosine similarity between `all-MiniLM-L6-v2` embeddings — no external API needed.

---

## License

MIT

