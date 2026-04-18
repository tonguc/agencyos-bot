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
        className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-colors ${
          active === null
            ? "bg-slate-900 text-white border-slate-900"
            : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
        }`}
      >
        Hepsi · {summary.total}
      </button>
      {ORDER.map((seg) => {
        const c = SEGMENT_COLORS[seg];
        const isActive = active === seg;
        const count = summary[seg];
        return (
          <button
            key={seg}
            type="button"
            onClick={() => onToggle(isActive ? null : seg)}
            className={`text-xs font-medium px-3 py-1.5 rounded-full border inline-flex items-center gap-2 transition-colors ${
              isActive
                ? `${c.bg} ${c.text} ${c.border} ring-2 ${c.ring}`
                : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
            }`}
          >
            <span className={`h-2 w-2 rounded-full ${c.dot}`} />
            {SEGMENT_LABELS[seg]} · {count}
          </button>
        );
      })}
    </div>
  );
}
