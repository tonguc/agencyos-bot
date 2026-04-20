"use client";

import { Search, Sparkles } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";

const EXAMPLES = [
  "kadıköyde diş hekimi",
  "beşiktaş psikolog",
  "kaş'ta restoran",
  "ankara avukat",
  "izmirde lazer epilasyon",
  "esenyurt tesisatçı",
];

interface Props {
  value: string;
  loading: boolean;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onPickExample: (q: string) => void;
}

export function SearchInput({ value, loading, onChange, onSubmit, onPickExample }: Props) {
  return (
    <div className="space-y-3">
      <form
        onSubmit={(e) => { e.preventDefault(); onSubmit(); }}
        className="flex items-stretch gap-2"
      >
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-dim" />
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Ne arıyorsun?  (örn: kadıköyde estetik diş hekimi)"
            className="w-full pl-10 pr-4 py-3 font-mono text-sm border border-stroke bg-panel text-bright placeholder:text-dim focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-all"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="inline-flex items-center gap-2 px-5 border border-accent bg-accent/10 text-accent font-mono text-[12px] uppercase tracking-wider hover:bg-accent/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          {loading ? <Spinner className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}
          {loading ? "Aranıyor..." : "Ara"}
        </button>
      </form>

      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[11px] text-dim tracking-[0.2em] uppercase">Örnek:</span>
        {EXAMPLES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPickExample(q)}
            className="font-mono text-[11px] px-2.5 py-1 border border-stroke text-muted hover:border-accent hover:text-bright transition-all"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
