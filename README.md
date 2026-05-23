---
title: Chat With Any Document
emoji: 📄
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: 1.57.0
app_file: app.py
pinned: false
license: mit
---

<h1 align="center">📄 Chat with Any Document</h1>

<p align="center">
  A production-ready RAG (Retrieval-Augmented Generation) pipeline that lets you upload a PDF or paste any URL and have a full conversation with its contents.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B?logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/LangChain-0.2%2B-1C3C3C?logo=langchain&logoColor=white" />
  <img src="https://img.shields.io/badge/FAISS-CPU-orange" />
  <img src="https://img.shields.io/badge/Embeddings-Local%20CPU-green" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" />
</p>

---

> **Embeddings run entirely on your CPU using `sentence-transformers` — only LLM calls use your OpenAI API key.**

---

## ✨ Features

| Feature | Details |
|---|---|
| 📂 Document Sources | Upload a PDF **or** paste any web URL |
| ✂️ Smart Chunking | Recursive character splitter with configurable size & overlap |
| 🧠 Local Embeddings | `sentence-transformers/all-MiniLM-L6-v2` — no extra API key needed |
| ⚡ Fast Retrieval | FAISS vector store with cosine similarity |
| 💬 Chat Interface | Full multi-turn conversation with memory |
| 🔍 Context Inspector | Side panel shows retrieved chunks + relevance scores |
| 🤖 Model Selector | Choose between `gpt-4o-mini`, `gpt-3.5-turbo`, `gpt-4o` |
| 🎛️ Tunable Parameters | Chunk size, chunk overlap, top-K from the sidebar |

---

## 🏗️ Architecture

```
  ┌──────────────────────────────────────────────┐
  │              Document Ingestion               │
  │   PDF (PyPDF)  ──or──  URL (WebBaseLoader)   │
  └────────────────────┬─────────────────────────┘
                       │
                       ▼
  ┌──────────────────────────────────────────────┐
  │           Recursive Text Splitter             │
  │    chunk_size=1000  |  chunk_overlap=150      │
  └────────────────────┬─────────────────────────┘
                       │
                       ▼
  ┌──────────────────────────────────────────────┐
  │         HuggingFace Embeddings (CPU)          │
  │       sentence-transformers/all-MiniLM-L6-v2  │
  └────────────────────┬─────────────────────────┘
                       │
                       ▼
  ┌──────────────────────────────────────────────┐
  │            FAISS Vector Store                 │
  └────────────────────┬─────────────────────────┘
                       │
       User Question ──┤
                       ▼
  ┌──────────────────────────────────────────────┐
  │         Similarity Search → Top-K Chunks      │
  └────────────────────┬─────────────────────────┘
                       │
                       ▼
  ┌──────────────────────────────────────────────┐
  │        OpenAI LLM  (gpt-4o-mini etc.)         │
  │   Context + Question → Grounded Answer        │
  └──────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
RAG/
├── app.py                  # Streamlit app — UI, chat, sidebar
├── requirements.txt        # All dependencies
├── .env.example            # Environment variable template
└── src/
    ├── __init__.py
    ├── document_loader.py  # PDF & URL ingestion
    ├── chunker.py          # Recursive text splitter
    ├── vector_store.py     # FAISS index + HuggingFace embeddings
    └── rag_chain.py        # Retrieval + LLM answer generation
```

---

## 🚀 Quickstart

### 1. Clone the repo

```bash
git clone https://github.com/apatha32/RAG-Agent-AskMyDoc.git
cd RAG-Agent-AskMyDoc
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> First run downloads the `all-MiniLM-L6-v2` embedding model (~80 MB) once and caches it locally.

### 4. Set your OpenAI API key

```bash
cp .env.example .env
# Open .env and add:  OPENAI_API_KEY=sk-...
```

### 5. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🛠️ Usage

1. Enter your **OpenAI API key** in the sidebar
2. Choose **Upload PDF** or **Enter URL**
3. Tune chunk size, overlap, and top-K if needed
4. Click **⚡ Process Document**
5. Ask questions in the chat — retrieved chunks appear in the right panel with relevance scores

---

## ☁️ Deploy on Hugging Face Spaces

1. Go to **[huggingface.co/new-space](https://huggingface.co/new-space)**
2. Set **Space name** (e.g. `chat-with-any-document`)
3. Select **Streamlit** as the SDK *(auto-detected from README frontmatter)*
   - Under **Files**, choose **"Import from GitHub"** → paste `https://github.com/apatha32/RAG-Agent-AskMyDoc`
5. Go to **Settings → Variables and secrets** → add your secrets:

   | Secret | Required for |
   |---|---|
   | `OPENAI_API_KEY` | OpenAI provider (gpt-4o-mini etc.) |
   | `HF_TOKEN` | HuggingFace free models (Mistral, Zephyr, Llama) |

6. The Space builds automatically (~2 min) and goes live at:
   `https://huggingface.co/spaces/<your-username>/<space-name>`

> **Tip:** You only need one of the two secrets. Add `HF_TOKEN` alone to run entirely for free.

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | For OpenAI models | Get it at [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `HF_TOKEN` | For free HF models | Get it at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

---

## 🧰 Tech Stack

- **[Streamlit](https://streamlit.io/)** — UI framework
- **[LangChain](https://langchain.com/)** — RAG orchestration
- **[FAISS](https://github.com/facebookresearch/faiss)** — Vector similarity search
- **[sentence-transformers](https://sbert.net/)** — Local CPU embeddings
- **[OpenAI](https://openai.com/)** — Paid LLM option
- **[HuggingFace](https://huggingface.co/)** — Free LLM option (Mistral, Zephyr, Llama)
- **[PyPDF](https://pypdf.readthedocs.io/)** — PDF text extraction

---

## 📄 License

MIT
