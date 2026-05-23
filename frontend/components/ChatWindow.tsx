"use client";
import { useEffect, useRef, useState } from "react";
import { Send, Square, Bot } from "lucide-react";
import { MessageBubble, Message } from "./MessageBubble";
import { AgentStep } from "./AgentTrace";

interface Props {
  apiUrl: string;
  provider: string;
  openaiKey: string;
  hfToken: string;
  docsLoaded: boolean;
}

const WELCOME: Message = {
  role: "assistant",
  content:
    "Hello! I'm your AI research assistant. Upload a document on the left and I'll answer questions about it using hybrid retrieval — or ask me anything and I'll search the web.",
};

export function ChatWindow({ apiUrl, provider, openaiKey, hfToken, docsLoaded }: Props) {
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  async function send() {
    const text = input.trim();
    if (!text || streaming) return;

    // Append user message
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setStreaming(true);

    // Placeholder assistant message
    const assistantIdx = messages.length + 1;
    setMessages((m) => [
      ...m,
      { role: "assistant", content: "", streaming: true, steps: [] },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`${apiUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          provider,
          openai_api_key: openaiKey || undefined,
          hf_token: hfToken || undefined,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          let event: { type: string; content?: string; name?: string; input?: string; output?: string; message?: string };
          try {
            event = JSON.parse(raw);
          } catch {
            continue;
          }

          if (event.type === "token") {
            setMessages((m) => {
              const copy = [...m];
              const last = { ...copy[copy.length - 1] };
              last.content += event.content ?? "";
              copy[copy.length - 1] = last;
              return copy;
            });
          } else if (event.type === "tool_start" || event.type === "tool_end") {
            const step: AgentStep = {
              type: event.type,
              name: event.name ?? "",
              content: event.type === "tool_start" ? (event.input ?? "") : (event.output ?? ""),
            };
            setMessages((m) => {
              const copy = [...m];
              const last = { ...copy[copy.length - 1] };
              last.steps = [...(last.steps ?? []), step];
              copy[copy.length - 1] = last;
              return copy;
            });
          } else if (event.type === "done") {
            setMessages((m) => {
              const copy = [...m];
              const last = { ...copy[copy.length - 1], streaming: false };
              copy[copy.length - 1] = last;
              return copy;
            });
          } else if (event.type === "error") {
            setMessages((m) => {
              const copy = [...m];
              const last = {
                ...copy[copy.length - 1],
                content: `⚠️ ${event.message}`,
                streaming: false,
              };
              copy[copy.length - 1] = last;
              return copy;
            });
          }
        }
      }
    } catch (e: unknown) {
      if ((e as Error).name !== "AbortError") {
        setMessages((m) => {
          const copy = [...m];
          const last = {
            ...copy[copy.length - 1],
            content: `⚠️ ${(e as Error).message}`,
            streaming: false,
          };
          copy[copy.length - 1] = last;
          return copy;
        });
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }

  function stop() {
    abortRef.current?.abort();
    setStreaming(false);
    setMessages((m) => {
      const copy = [...m];
      if (copy[copy.length - 1]?.streaming) {
        copy[copy.length - 1] = { ...copy[copy.length - 1], streaming: false };
      }
      return copy;
    });
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-surface-border">
        {!docsLoaded && (
          <div className="flex items-center gap-2 text-[11px] text-amber-500/80 bg-amber-500/5 border border-amber-500/20 rounded-lg px-3 py-2 mb-3">
            <Bot className="w-3.5 h-3.5 flex-shrink-0" />
            No document loaded — I'll rely on web search or general knowledge.
          </div>
        )}
        <div className="flex gap-2 items-end bg-surface-card border border-surface-border rounded-xl px-3 py-2 focus-within:border-indigo-500/60 transition-colors">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Ask anything about your document…"
            className="flex-1 bg-transparent text-sm text-zinc-200 placeholder-zinc-600 resize-none focus:outline-none max-h-32"
          />
          <button
            onClick={streaming ? stop : send}
            disabled={!streaming && !input.trim()}
            className={`flex-shrink-0 p-1.5 rounded-lg transition-colors ${
              streaming
                ? "text-red-400 hover:bg-red-500/10"
                : input.trim()
                ? "text-indigo-400 hover:bg-indigo-500/10"
                : "text-zinc-700 cursor-not-allowed"
            }`}
          >
            {streaming ? (
              <Square className="w-4 h-4 fill-current" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
        <p className="text-[11px] text-zinc-700 mt-1.5 text-center">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
