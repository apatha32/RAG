"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Bot } from "lucide-react";
import { AgentTrace, AgentStep } from "./AgentTrace";
import { SourceCitations } from "./SourceCitation";
import { EvalPanel } from "./EvalPanel";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Message {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  steps?: AgentStep[];
  question?: string; // paired user question for eval
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 animate-slide-up ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mt-0.5 ${
          isUser
            ? "bg-indigo-600 text-white"
            : "bg-surface-card border border-surface-border text-indigo-400"
        }`}
      >
        {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
      </div>

      {/* Bubble */}
      <div className={`max-w-[80%] space-y-1 ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        <div
          className={`px-4 py-3 rounded-2xl text-sm ${
            isUser
              ? "bg-indigo-600 text-white rounded-tr-sm"
              : "bg-surface-card border border-surface-border text-zinc-200 rounded-tl-sm"
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className={`prose-chat ${message.streaming ? "streaming-cursor" : ""}`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content || " "}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Agent trace (only for assistant) */}
        {!isUser && message.steps && message.steps.length > 0 && (
          <div className="w-full">
            <AgentTrace steps={message.steps} />
          </div>
        )}

        {/* Source citations */}
        {!isUser && !message.streaming && message.content && (
          <SourceCitations text={message.content} />
        )}

        {/* Evaluation panel */}
        {!isUser && !message.streaming && message.content && message.question && (
          <EvalPanel question={message.question} answer={message.content} apiUrl={API_URL} />
        )}
      </div>
    </div>
  );
}
