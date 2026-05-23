"""
Chat with Any Document — Streamlit app
A RAG pipeline that lets you upload a PDF or paste a URL and chat with its content.
"""
import os
import streamlit as st
from dotenv import load_dotenv

from src.document_loader import load_pdf, load_url
from src.chunker import chunk_documents
from src.vector_store import build_vector_store
from src.rag_chain import answer_question, HF_MODELS

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Chat with Any Document",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Chat with Any Document")
st.caption("Upload a PDF or enter a URL — then ask anything about it.")

# ── Session state init ────────────────────────────────────────────────────────
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []   # list of {"role": ..., "content": ...}
if "doc_name" not in st.session_state:
    st.session_state.doc_name = None
if "last_sources" not in st.session_state:
    st.session_state.last_sources = []

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")

    provider = st.radio(
        "LLM Provider",
        options=["OpenAI", "HuggingFace (Free)"],
        horizontal=True,
        help="HuggingFace uses the free Inference API — just provide a HF token.",
    )

    openai_key = ""
    hf_token = ""
    model_name = ""

    if provider == "OpenAI":
        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
            placeholder="sk-...",
            help="Your OpenAI API key. Never stored beyond this session.",
        )
        model_name = st.selectbox(
            "Model",
            options=["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o"],
            index=0,
            help="gpt-4o-mini is fastest and cheapest.",
        )
    else:
        hf_token = st.text_input(
            "HuggingFace Token",
            type="password",
            value=os.getenv("HF_TOKEN", ""),
            placeholder="hf_...",
            help="Free token from huggingface.co/settings/tokens",
        )
        st.caption("Get a free token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)")
        model_name = st.selectbox(
            "Model",
            options=HF_MODELS,
            index=0,
            help="All models run via the HuggingFace Inference API at no cost.",
        )

    st.divider()
    st.subheader("📥 Load Document")

    source_type = st.radio("Source", ["Upload PDF", "Enter URL"], horizontal=True)

    if source_type == "Upload PDF":
        uploaded_file = st.file_uploader("Choose a PDF", type=["pdf"])
    else:
        url_input = st.text_input("URL", placeholder="https://example.com/article")

    st.divider()
    st.subheader("🔧 Chunking Settings")

    chunk_size = st.slider("Chunk size (tokens)", 300, 2000, 1000, step=100)
    chunk_overlap = st.slider("Chunk overlap", 0, 400, 150, step=50)
    top_k = st.slider("Top-K retrieved chunks", 2, 8, 4)

    st.divider()
    process_btn = st.button("⚡ Process Document", use_container_width=True, type="primary")

    # ── Process document ──────────────────────────────────────────────────────
    if process_btn:
        api_ready = (provider == "OpenAI" and openai_key) or (provider == "HuggingFace (Free)" and hf_token)
        if not api_ready:
            st.error("Please enter your API key above.")
        elif source_type == "Upload PDF" and not uploaded_file:
            st.error("Please upload a PDF file.")
        elif source_type == "Enter URL" and not url_input.strip():
            st.error("Please enter a URL.")
        else:
            with st.spinner("Loading document…"):
                try:
                    if source_type == "Upload PDF":
                        docs = load_pdf(uploaded_file.read(), uploaded_file.name)
                        doc_label = uploaded_file.name
                    else:
                        docs = load_url(url_input.strip())
                        doc_label = url_input.strip()
                except Exception as e:
                    st.error(f"Failed to load document: {e}")
                    st.stop()

            with st.spinner("Chunking & embedding (first run downloads ~80 MB model)…"):
                try:
                    chunks = chunk_documents(docs, chunk_size, chunk_overlap)
                    vector_store = build_vector_store(chunks)
                except Exception as e:
                    st.error(f"Failed to build vector store: {e}")
                    st.stop()

            st.session_state.vector_store = vector_store
            st.session_state.doc_name = doc_label
            st.session_state.chat_history = []
            st.session_state.last_sources = []
            st.success(f"✅ Indexed **{len(chunks)}** chunks from **{doc_label}**")

    # Status badge
    if st.session_state.doc_name:
        st.info(f"📂 Active: **{st.session_state.doc_name}**")

    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.last_sources = []
        st.rerun()

# ── Main chat area ────────────────────────────────────────────────────────────
col_chat, col_context = st.columns([2, 1])

with col_chat:
    # Render chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    user_input = st.chat_input(
        "Ask a question about the document…",
        disabled=st.session_state.vector_store is None,
    )

    if user_input:
        api_ready = (provider == "OpenAI" and openai_key) or (provider == "HuggingFace (Free)" and hf_token)
        if not api_ready:
            st.error("Please enter your API key in the sidebar.")
            st.stop()

        # Show user message immediately
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Generate answer
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    result = answer_question(
                        st.session_state.vector_store,
                        user_input,
                        provider=provider.split(" ")[0].lower(),
                        model_name=model_name,
                        openai_api_key=openai_key or None,
                        hf_token=hf_token or None,
                        k=top_k,
                    )
                    answer = result["answer"]
                    st.session_state.last_sources = result["sources"]
                except Exception as e:
                    answer = f"⚠️ Error: {e}"
                    st.session_state.last_sources = []

            st.markdown(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})

with col_context:
    st.subheader("🔍 Retrieved Context")
    if st.session_state.last_sources:
        for i, (doc, score) in enumerate(st.session_state.last_sources, 1):
            source_label = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page", "")
            page_str = f" · page {int(page) + 1}" if page != "" else ""
            relevance = round((1 - score) * 100, 1) if score <= 1 else round(100 / (1 + score), 1)

            with st.expander(f"Chunk {i} — {source_label}{page_str}  ({relevance}% relevance)"):
                st.caption(f"Score: `{score:.4f}`")
                st.write(doc.page_content)
    else:
        st.caption("Retrieved chunks will appear here after you ask a question.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Built with LangChain · FAISS · sentence-transformers · Streamlit | "
    "Embeddings run locally — only LLM calls use your OpenAI key."
)
