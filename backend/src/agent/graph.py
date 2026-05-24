"""
LangGraph ReAct agent — supports model selection and conversation history.
"""
from typing import Optional
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from langgraph.prebuilt import ToolNode

from src.agent.tools import make_rag_tool, make_web_search_tool

SYSTEM_PROMPT = """You are a helpful research assistant with access to two tools:

1. **rag_search** — searches the user's uploaded document(s). Always try this first for document-specific questions.
2. **web_search** — searches the web for general or real-time information.

Guidelines:
- Use rag_search for questions about the uploaded document.
- Use web_search when the document doesn't contain the answer or for current events.
- You may call multiple tools in sequence if needed.
- Always cite sources using the [Chunk N | ...] format from rag_search results.
- Be concise but thorough."""

OPENAI_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
HF_MODELS = {
    "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3",
    "zephyr-7b": "HuggingFaceH4/zephyr-7b-beta",
    "llama-3": "meta-llama/Llama-3.2-3B-Instruct",
}


def create_agent(
    vector_store,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    openai_api_key: Optional[str] = None,
    hf_token: Optional[str] = None,
):
    tools = [make_rag_tool(vector_store), make_web_search_tool()]
    tool_node = ToolNode(tools)

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=model if model in OPENAI_MODELS else "gpt-4o-mini",
            api_key=openai_api_key,
            temperature=0,
            streaming=True,
        )
    else:
        from langchain_huggingface import HuggingFaceEndpoint
        repo_id = HF_MODELS.get(model, "mistralai/Mistral-7B-Instruct-v0.3")
        llm = HuggingFaceEndpoint(
            repo_id=repo_id,
            huggingfacehub_api_token=hf_token,
            temperature=0.1,
            max_new_tokens=1024,
            streaming=True,
        )

    llm_with_tools = llm.bind_tools(tools)

    def call_model(state: MessagesState):
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: MessagesState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()
