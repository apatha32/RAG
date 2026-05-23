"""
LangGraph ReAct agent with RAG + web search tools.
Streams events back to the FastAPI endpoint.
"""
from typing import Optional
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from langgraph.prebuilt import ToolNode

from src.agent.tools import make_rag_tool, make_web_search_tool

SYSTEM_PROMPT = """You are a helpful research assistant with access to two tools:

1. **rag_search** — searches the user's uploaded document. Always try this first for document-specific questions.
2. **web_search** — searches the web for general or real-time information.

Guidelines:
- Use rag_search for questions about the uploaded document.
- Use web_search when the document doesn't contain the answer or for current events.
- You may call multiple tools in sequence if needed.
- Always cite your sources in the final answer.
- Be concise but thorough."""


def create_agent(
    vector_store,
    provider: str = "openai",
    openai_api_key: Optional[str] = None,
    hf_token: Optional[str] = None,
):
    # Build tools
    tools = [make_rag_tool(vector_store), make_web_search_tool()]
    tool_node = ToolNode(tools)

    # Build LLM
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=openai_api_key,
            temperature=0,
            streaming=True,
        )
    else:
        from langchain_huggingface import HuggingFaceEndpoint
        llm = HuggingFaceEndpoint(
            repo_id="mistralai/Mistral-7B-Instruct-v0.3",
            huggingfacehub_api_token=hf_token,
            temperature=0.1,
            max_new_tokens=1024,
            streaming=True,
        )

    llm_with_tools = llm.bind_tools(tools)

    def call_model(state: MessagesState):
        messages = state["messages"]
        # Prepend system message if not already present
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
