"use client";
import { ChevronDown, ChevronRight, Wrench, Globe, FileSearch } from "lucide-react";
import { useState } from "react";

export interface AgentStep {
  type: "tool_start" | "tool_end";
  name: string;
  content: string;
}

const TOOL_ICONS: Record<string, React.ReactNode> = {
  rag_search: <FileSearch className="w-3.5 h-3.5" />,
  web_search: <Globe className="w-3.5 h-3.5" />,
};

const TOOL_COLORS: Record<string, string> = {
  rag_search: "text-indigo-400 border-indigo-500/30 bg-indigo-500/5",
  web_search: "text-emerald-400 border-emerald-500/30 bg-emerald-500/5",
};

export function AgentTrace({ steps }: { steps: AgentStep[] }) {
  const [open, setOpen] = useState(false);
  if (steps.length === 0) return null;

  // Group start + end pairs
  const pairs: { name: string; input: string; output?: string }[] = [];
  for (const step of steps) {
    if (step.type === "tool_start") {
      pairs.push({ name: step.name, input: step.content });
    } else if (step.type === "tool_end" && pairs.length > 0) {
      const last = pairs[pairs.length - 1];
      if (last.name === step.name) last.output = step.content;
    }
  }

  return (
    <div className="mt-2 border border-surface-border rounded-lg overflow-hidden text-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 w-full px-3 py-2 bg-surface-card hover:bg-surface-hover text-zinc-400 transition-colors"
      >
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        <Wrench className="w-3.5 h-3.5" />
        <span className="font-medium">
          Agent used {pairs.length} tool{pairs.length !== 1 ? "s" : ""}
        </span>
      </button>

      {open && (
        <div className="divide-y divide-surface-border">
          {pairs.map((p, i) => {
            const colorClass = TOOL_COLORS[p.name] ?? "text-violet-400 border-violet-500/30 bg-violet-500/5";
            return (
              <div key={i} className="px-3 py-2.5 space-y-1.5 bg-surface">
                {/* Tool name */}
                <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[11px] font-semibold ${colorClass}`}>
                  {TOOL_ICONS[p.name] ?? <Wrench className="w-3 h-3" />}
                  {p.name}
                </div>
                {/* Input */}
                <div>
                  <span className="text-zinc-500 uppercase tracking-wider text-[10px] font-semibold">Input</span>
                  <pre className="mt-0.5 text-zinc-400 whitespace-pre-wrap break-words">{p.input}</pre>
                </div>
                {/* Output */}
                {p.output && (
                  <div>
                    <span className="text-zinc-500 uppercase tracking-wider text-[10px] font-semibold">Output</span>
                    <pre className="mt-0.5 text-zinc-500 whitespace-pre-wrap break-words line-clamp-4">{p.output}</pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
