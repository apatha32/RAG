"use client";
import { useEffect, useRef, useState } from "react";
import { Upload, Link, Loader2, CheckCircle, Trash2, ChevronDown, ChevronUp, Settings, FileText } from "lucide-react";

const STRATEGIES = [
  {
    id: "recursive",
    label: "Recursive",
    description: "Splits on paragraphs → sentences → words. Best general purpose.",
  },
  {
    id: "fixed",
    label: "Fixed Size",
    description: "Simple fixed-character splits. Fast, no structure awareness.",
  },
  {
    id: "semantic",
    label: "Semantic",
    description: "Groups semantically similar sentences using embeddings.",
  },
  {
    id: "sentence_window",
    label: "Sentence Window",
    description: "Each sentence + surrounding context window (±2 sentences).",
  },
];

interface Doc {
  id: string;
  name: string;
  chunks: number;
  strategy: string;
  pages: number;
}

interface IngestResult {
  doc_id: string;
  chunks: number;
  strategy: string;
  pages: number;
}

interface Props {
  onIngest: (result: IngestResult) => void;
  onClear: () => void;
  apiUrl: string;
}

export function DocumentPanel({ onIngest, onClear, apiUrl }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [strategy, setStrategy] = useState("recursive");
  const [chunkSize, setChunkSize] = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(150);
  const [urlValue, setUrlValue] = useState("");
  const [mode, setMode] = useState<"file" | "url">("file");
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [result, setResult] = useState<IngestResult | null>(null);
  const [error, setError] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [docs, setDocs] = useState<Doc[]>([]);

  const refreshDocs = async () => {
    try {
      const res = await fetch(`${apiUrl}/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocs(data.documents ?? []);
      }
    } catch {}
  };

  useEffect(() => { refreshDocs(); }, []);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f?.type === "application/pdf") setFile(f);
  };

  async function submit() {
    setStatus("loading");
    setError("");
    setResult(null);

    const form = new FormData();
    form.append("strategy", strategy);
    form.append("chunk_size", String(chunkSize));
    form.append("chunk_overlap", String(chunkOverlap));

    if (mode === "file" && file) {
      form.append("file", file);
    } else if (mode === "url" && urlValue) {
      form.append("url", urlValue);
    } else {
      setError("Please select a file or enter a URL.");
      setStatus("error");
      return;
    }

    try {
      const res = await fetch(`${apiUrl}/ingest`, { method: "POST", body: form });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${res.status}`);
      }
      const data: IngestResult = await res.json();
      setResult(data);
      setStatus("done");
      onIngest(data);
      await refreshDocs();
    } catch (e) {
      setError(String(e));
      setStatus("error");
    }
  }

  async function clear() {
    await fetch(`${apiUrl}/collection`, { method: "DELETE" });
    setFile(null);
    setResult(null);
    setStatus("idle");
    setUrlValue("");
    setDocs([]);
    onClear();
  }

  async function deleteDoc(docId: string) {
    await fetch(`${apiUrl}/documents/${docId}`, { method: "DELETE" });
    await refreshDocs();
    if (docs.length <= 1) onClear();
  }

  return (
    <div className="flex flex-col gap-4 h-full overflow-y-auto pr-1">
      {/* Header */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-100">Document</h2>
        <p className="text-xs text-zinc-500 mt-0.5">Upload a PDF or paste a URL to get started</p>
      </div>

      {/* Mode toggle */}
      <div className="flex rounded-lg border border-surface-border overflow-hidden text-xs">
        {(["file", "url"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`flex-1 py-1.5 transition-colors font-medium capitalize ${
              mode === m
                ? "bg-indigo-600 text-white"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-surface-hover"
            }`}
          >
            {m === "file" ? "PDF File" : "Web URL"}
          </button>
        ))}
      </div>

      {/* Input area */}
      {mode === "file" ? (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onClick={() => fileRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
            dragging
              ? "border-indigo-500 bg-indigo-500/5"
              : file
              ? "border-indigo-500/50 bg-indigo-500/5"
              : "border-surface-border hover:border-zinc-600"
          }`}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
          />
          <Upload className="w-5 h-5 mx-auto mb-2 text-zinc-500" />
          {file ? (
            <p className="text-xs text-indigo-400 font-medium truncate">{file.name}</p>
          ) : (
            <>
              <p className="text-xs text-zinc-400">Drag & drop PDF or click to browse</p>
              <p className="text-[11px] text-zinc-600 mt-0.5">PDF files only</p>
            </>
          )}
        </div>
      ) : (
        <div className="relative">
          <Link className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
          <input
            type="url"
            placeholder="https://example.com/article"
            value={urlValue}
            onChange={(e) => setUrlValue(e.target.value)}
            className="w-full bg-surface-card border border-surface-border rounded-lg pl-8 pr-3 py-2 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
      )}

      {/* Chunking Strategy */}
      <div>
        <p className="text-xs font-medium text-zinc-400 mb-2">Chunking Strategy</p>
        <div className="space-y-1.5">
          {STRATEGIES.map((s) => (
            <label
              key={s.id}
              className={`flex gap-2.5 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                strategy === s.id
                  ? "border-indigo-500/60 bg-indigo-500/8"
                  : "border-surface-border hover:border-zinc-600"
              }`}
            >
              <input
                type="radio"
                name="strategy"
                value={s.id}
                checked={strategy === s.id}
                onChange={() => setStrategy(s.id)}
                className="mt-0.5 accent-indigo-500 flex-shrink-0"
              />
              <div>
                <p className="text-xs font-medium text-zinc-200">{s.label}</p>
                <p className="text-[11px] text-zinc-500 leading-tight mt-0.5">{s.description}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Advanced settings */}
      <div>
        <button
          onClick={() => setShowAdvanced((v) => !v)}
          className="flex items-center gap-1.5 text-[11px] text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <Settings className="w-3 h-3" />
          Advanced settings
          {showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>

        {showAdvanced && (
          <div className="mt-3 space-y-3 pl-1">
            <div>
              <div className="flex justify-between text-[11px] text-zinc-400 mb-1">
                <span>Chunk size</span>
                <span className="font-mono text-indigo-400">{chunkSize}</span>
              </div>
              <input
                type="range"
                min={200}
                max={4000}
                step={100}
                value={chunkSize}
                onChange={(e) => setChunkSize(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
            </div>
            <div>
              <div className="flex justify-between text-[11px] text-zinc-400 mb-1">
                <span>Chunk overlap</span>
                <span className="font-mono text-indigo-400">{chunkOverlap}</span>
              </div>
              <input
                type="range"
                min={0}
                max={500}
                step={25}
                value={chunkOverlap}
                onChange={(e) => setChunkOverlap(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
            </div>
          </div>
        )}
      </div>

      {/* Ingested documents list */}
      {docs.length > 0 && (
        <div>
          <p className="text-xs font-medium text-zinc-400 mb-2">Ingested Documents ({docs.length})</p>
          <div className="space-y-1.5">
            {docs.map((doc) => (
              <div key={doc.id} className="flex items-center gap-2 p-2 rounded-lg bg-surface-card border border-surface-border text-xs">
                <FileText className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-zinc-200 truncate font-medium">{doc.name}</p>
                  <p className="text-zinc-500 text-[11px]">{doc.chunks} chunks · {doc.pages} pp · {doc.strategy}</p>
                </div>
                <button
                  onClick={() => deleteDoc(doc.id)}
                  className="text-zinc-600 hover:text-red-400 transition-colors flex-shrink-0"
                  title="Remove document"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Submit / Clear */}
      <button
        onClick={submit}
        disabled={status === "loading"}
        className="flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold py-2.5 rounded-xl transition-colors"
      >
        {status === "loading" ? (
          <>
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Processing…
          </>
        ) : (
          "Process Document"
        )}
      </button>

      {/* Status */}
      {status === "done" && result && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-emerald-500/8 border border-emerald-500/20 text-xs">
          <CheckCircle className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
          <div className="text-emerald-300">
            <p className="font-medium">Document indexed</p>
            <p className="text-emerald-400/70 mt-0.5">
              {result.chunks} chunks · {result.pages} pages · {result.strategy}
            </p>
          </div>
        </div>
      )}

      {status === "error" && (
        <div className="p-3 rounded-lg bg-red-500/8 border border-red-500/20 text-xs text-red-400">
          {error}
        </div>
      )}

      {status === "done" && (
        <button
          onClick={clear}
          className="flex items-center gap-2 text-xs text-zinc-600 hover:text-red-400 transition-colors"
        >
          <Trash2 className="w-3 h-3" />
          Clear document
        </button>
      )}
    </div>
  );
}
