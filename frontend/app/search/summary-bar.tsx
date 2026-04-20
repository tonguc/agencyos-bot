"use client";

import type { SearchSegment, SearchSummary } from "@/types";
import { SEGMENT_COLORS, SEGMENT_LABELS } from "./segment";

interface Props {
  summary: SearchSummary;
  active: SearchSegment | null;
  onToggle: (s: SearchSegment | null) => void;
}

const ORDER: SearchSegment[] = ["hot", "warm", "review", "ok", "low"];

export function SummaryBar({ summary, active, onToggle }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={() => onToggle(null)}
        className={`font-mono text-[9px] tracking-[0.2em] uppercase px-3 py-1.5 border rounded-sm transition-all ${
          active === null
            ? "bg-accent/10 text-accent border-accent"
            : "bg-transparent text-muted border-stroke hover:border-stroke-2 hover:text-bright"
        }`}
      >
        HEPSI · {summary.total}
      </button>
      {ORDER.map((seg) => {
        const c = SEGMENT_COLORS[seg];
        const isActive = active === seg;
        const count = summary[seg];
        const isEmpty = count === 0;
        return (
          <button
            key={seg}
            type="button"
            disabled={isEmpty}
            onClick={() => onToggle(isActive ? null : seg)}
            className={`font-mono text-[9px] tracking-[0.2em] uppercase px-3 py-1.5 border rounded-sm inline-flex items-center gap-2 transition-all ${
              isEmpty
                ? "text-dim/50 border-stroke/50 cursor-not-allowed opacity-40"
                : isActive
                ? `${c.text} ${c.border} bg-panel-high`
                : "text-muted border-stroke hover:border-stroke-2 hover:text-bright"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${c.dot} ${isEmpty ? "opacity-40" : ""}`}
              style={isActive && !isEmpty ? { boxShadow: `0 0 5px ${c.color}` } : undefined}
            />
            {SEGMENT_LABELS[seg]} · {count}
          </button>
        );
      })}
    </div>
  );
}
