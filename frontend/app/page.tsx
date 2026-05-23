"use client";
import { useState } from "react";
import { DocumentPanel } from "@/components/DocumentPanel";
import { ChatWindow } from "@/components/ChatWindow";
import { Settings, X, KeyRound, Brain, PanelLeftClose, PanelLeftOpen } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [docsLoaded, setDocsLoaded] = useState(false);
  const [provider, setProvider] = useState("openai");
  const [openaiKey, setOpenaiKey] = useState("");
  const [hfToken, setHfToken] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex flex-col h-screen">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-surface-border bg-surface-card flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="text-zinc-500 hover:text-zinc-300 transition-colors"
            title="Toggle sidebar"
          >
            {sidebarOpen ? (
              <PanelLeftClose className="w-4 h-4" />
            ) : (
              <PanelLeftOpen className="w-4 h-4" />
            )}
          </button>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <Brain className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-semibold text-zinc-100 text-sm tracking-tight">AskMyDoc</span>
            <span className="text-[10px] text-zinc-600 font-medium border border-surface-border rounded px-1.5 py-0.5">
              Agent
            </span>
          </div>
        </div>

        <button
          onClick={() => setShowSettings((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <Settings className="w-3.5 h-3.5" />
          Keys
        </button>
      </header>

      {/* Settings drawer */}
      {showSettings && (
        <div className="border-b border-surface-border bg-surface-card px-4 py-3">
          <div className="max-w-xl mx-auto space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-medium text-zinc-400">
                <KeyRound className="w-3.5 h-3.5" /> API Keys
              </div>
              <button onClick={() => setShowSettings(false)} className="text-zinc-600 hover:text-zinc-400">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Provider toggle */}
            <div className="flex gap-2 text-xs">
              {(["openai", "huggingface"] as const).map((p) => (
                <button
                  key={p}
                  onClick={() => setProvider(p)}
                  className={`px-3 py-1.5 rounded-lg border font-medium transition-colors capitalize ${
                    provider === p
                      ? "bg-indigo-600 border-indigo-600 text-white"
                      : "border-surface-border text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  {p === "openai" ? "OpenAI" : "HuggingFace"}
                </button>
              ))}
            </div>

            {provider === "openai" ? (
              <input
                type="password"
                placeholder="sk-... (OpenAI API key)"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500 font-mono"
              />
            ) : (
              <input
                type="password"
                placeholder="hf_... (HuggingFace token)"
                value={hfToken}
                onChange={(e) => setHfToken(e.target.value)}
                className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500 font-mono"
              />
            )}
            <p className="text-[11px] text-zinc-600">Keys are stored only in browser memory and never sent to our servers.</p>
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex flex-1 min-h-0">
        {/* Sidebar */}
        {sidebarOpen && (
          <aside className="w-72 flex-shrink-0 border-r border-surface-border bg-surface-card p-4 overflow-y-auto">
            <DocumentPanel
              apiUrl={API_URL}
              onIngest={() => setDocsLoaded(true)}
              onClear={() => setDocsLoaded(false)}
            />
          </aside>
        )}

        {/* Chat */}
        <main className="flex-1 min-w-0 bg-surface">
          <ChatWindow
            apiUrl={API_URL}
            provider={provider}
            openaiKey={openaiKey}
            hfToken={hfToken}
            docsLoaded={docsLoaded}
          />
        </main>
      </div>
    </div>
  );
}
