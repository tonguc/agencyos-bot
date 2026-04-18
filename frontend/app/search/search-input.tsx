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
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Ne arıyorsun?  (örn: kadıköyde estetik diş hekimi)"
            className="w-full pl-11 pr-4 py-3.5 text-base rounded-xl border border-slate-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="inline-flex items-center gap-2 px-5 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? <Spinner className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
          {loading ? "Aranıyor..." : "Ara"}
        </button>
      </form>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-400">Örnek:</span>
        {EXAMPLES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPickExample(q)}
            className="text-xs px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 border border-slate-200 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
