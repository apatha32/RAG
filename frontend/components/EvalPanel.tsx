"use client";
import { BarChart3, Loader2 } from "lucide-react";
import { useState } from "react";

interface Scores {
  answer_relevancy: number;
  faithfulness: number;
  context_recall: number;
}

const LABELS: Record<string, string> = {
  answer_relevancy: "Answer Relevancy",
  faithfulness: "Faithfulness",
  context_recall: "Context Recall",
};

const COLORS: Record<string, string> = {
  answer_relevancy: "bg-indigo-500",
  faithfulness: "bg-emerald-500",
  context_recall: "bg-violet-500",
};

interface Props {
  question: string;
  answer: string;
  apiUrl: string;
}

export function EvalPanel({ question, answer, apiUrl }: Props) {
  const [scores, setScores] = useState<Scores | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${apiUrl}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, answer, contexts: [answer] }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setScores(await res.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  if (scores) {
    return (
      <div className="mt-2 p-3 rounded-lg bg-surface-card border border-surface-border text-xs space-y-2.5 animate-fade-in">
        <p className="text-zinc-500 font-medium uppercase tracking-wider text-[10px]">RAG Quality Metrics</p>
        {(Object.keys(scores) as Array<keyof Scores>).map((key) => (
          <div key={key}>
            <div className="flex justify-between text-zinc-400 mb-1">
              <span>{LABELS[key]}</span>
              <span className="font-mono text-zinc-300">{(scores[key] * 100).toFixed(0)}%</span>
            </div>
            <div className="h-1.5 bg-surface-border rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ${COLORS[key]}`}
                style={{ width: `${scores[key] * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <button
      onClick={run}
      disabled={loading}
      className="flex items-center gap-1.5 text-[11px] text-zinc-600 hover:text-zinc-400 transition-colors mt-1.5 disabled:cursor-not-allowed"
    >
      {loading ? (
        <Loader2 className="w-3 h-3 animate-spin" />
      ) : (
        <BarChart3 className="w-3 h-3" />
      )}
      {loading ? "Evaluating…" : "Evaluate response"}
      {error && <span className="text-red-500 ml-1">(failed)</span>}
    </button>
  );
}
