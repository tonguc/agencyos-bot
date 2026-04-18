"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { searchApi } from "@/lib/api";
import type { SearchResponse, SearchSegment } from "@/types";
import { SearchInput } from "./search-input";
import { SummaryBar } from "./summary-bar";
import { ResultCard } from "./result-card";
import { MapView } from "./map-view";

const RECENT_KEY = "agencyos.search.recent";
const RECENT_LIMIT = 6;

function loadRecent(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr.filter((x) => typeof x === "string").slice(0, RECENT_LIMIT) : [];
  } catch {
    return [];
  }
}

function saveRecent(q: string) {
  if (typeof window === "undefined") return;
  const cur = loadRecent();
  const next = [q, ...cur.filter((x) => x.toLowerCase() !== q.toLowerCase())].slice(0, RECENT_LIMIT);
  window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
}

export function SearchClient() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeSegment, setActiveSegment] = useState<SearchSegment | null>(null);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [recent, setRecent] = useState<string[]>([]);
  const reqId = useRef(0);

  useEffect(() => {
    // localStorage is client-only; load after hydration to avoid SSR mismatch.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRecent(loadRecent());
  }, []);

  const runSearch = useCallback(async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    const id = ++reqId.current;
    setLoading(true);
    setError(null);
    setSelectedIdx(null);
    setActiveSegment(null);
    try {
      const res = await searchApi.run(trimmed, 25);
      if (id !== reqId.current) return; // stale
      setData(res);
      saveRecent(trimmed);
      setRecent(loadRecent());
    } catch (e) {
      if (id !== reqId.current) return;
      setError(e instanceof Error ? e.message : "Arama başarısız");
      setData(null);
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  }, []);

  const handleSubmit = () => runSearch(query);
  const handleExample = (q: string) => { setQuery(q); runSearch(q); };

  const filtered = useMemo(() => {
    if (!data) return [];
    if (!activeSegment) return data.results.map((r, i) => ({ r, i }));
    return data.results
      .map((r, i) => ({ r, i }))
      .filter(({ r }) => r.segment === activeSegment);
  }, [data, activeSegment]);

  const parsed = data?.parsed;

  return (
    <div className="p-6 space-y-5">
      <SearchInput
        value={query}
        loading={loading}
        onChange={setQuery}
        onSubmit={handleSubmit}
        onPickExample={handleExample}
      />

      {!data && !loading && recent.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-400">Son aramalar:</span>
          {recent.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => handleExample(q)}
              className="text-xs px-2.5 py-1 rounded-full bg-white text-slate-600 border border-slate-200 hover:border-slate-300"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {!data && !loading && !error && (
        <div className="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center">
          <p className="text-sm text-slate-500">
            Ne tür bir firma bulmak istediğini doğal dilde yaz. Sonuçlar haritada gösterilir, skor ve segmente göre sıralanır.
          </p>
        </div>
      )}

      {data && (
        <>
          {parsed && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
              <span className="text-slate-400">Yorumlanan:</span>
              {parsed.city && <Tag k="Şehir" v={parsed.city} />}
              {parsed.district && <Tag k="İlçe" v={parsed.district} />}
              {parsed.sector && <Tag k="Sektör" v={parsed.sector} />}
              {parsed.sub_sector_hint && <Tag k="Alt" v={parsed.sub_sector_hint} />}
              <Tag k="Arama" v={parsed.search_string} />
            </div>
          )}

          <SummaryBar
            summary={data.summary}
            active={activeSegment}
            onToggle={setActiveSegment}
          />

          {data.results.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center">
              <p className="text-sm text-slate-500">{data.error || "Sonuç bulunamadı."}</p>
              <p className="text-xs text-slate-400 mt-2">
                Arama terimini sadeleştirmeyi dene veya şehir/ilçe ekle.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
              <div className="lg:col-span-2 space-y-3 lg:max-h-[calc(100vh-340px)] lg:overflow-y-auto pr-1">
                {filtered.length === 0 ? (
                  <p className="text-xs text-slate-400 italic px-1 py-4">
                    Bu segmentte sonuç yok.
                  </p>
                ) : (
                  filtered.map(({ r, i }) => (
                    <ResultCard
                      key={`${r.name}-${i}`}
                      lead={r}
                      selected={selectedIdx === i}
                      onSelect={() => setSelectedIdx(selectedIdx === i ? null : i)}
                    />
                  ))
                )}
              </div>
              <div className="lg:col-span-3 lg:sticky lg:top-4 lg:h-[calc(100vh-340px)]">
                <MapView
                  results={data.results}
                  selectedIdx={selectedIdx}
                  onSelect={setSelectedIdx}
                />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Tag({ k, v }: { k: string; v: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="text-slate-400">{k}:</span>
      <span className="font-medium text-slate-700">{v}</span>
    </span>
  );
}
