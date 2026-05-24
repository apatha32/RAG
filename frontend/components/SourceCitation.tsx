"use client";

/** Parses [Chunk N | file.pdf p.3 | strategy] citations from agent output. */
const CITATION_RE = /\[Chunk (\d+) \| ([^\]]+)\]/g;

interface Citation {
  id: string;
  label: string;
}

export function SourceCitations({ text }: { text: string }) {
  const citations: Citation[] = [];
  let match: RegExpExecArray | null;

  const re = new RegExp(CITATION_RE.source, "g");
  while ((match = re.exec(text)) !== null) {
    citations.push({ id: match[1], label: match[2] });
  }

  if (citations.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {citations.map((c, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] bg-indigo-500/10 border border-indigo-500/20 rounded-full text-indigo-400 font-mono"
          title={c.label}
        >
          [{c.id}] {c.label}
        </span>
      ))}
    </div>
  );
}
