"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { searchApi } from "@/lib/api";
import type { SearchResponse, SearchSegment } from "@/types";
import { SearchInput } from "./search-input";
import { SummaryBar } from "./summary-bar";
import { ResultCard } from "./result-card";
import { MapView } from "./map-view";

const RECENT_KEY  = "agencyos.search.recent";
const CACHE_KEY   = "agencyos.search.cache";
const RECENT_LIMIT = 6;
const LIMIT_OPTIONS = [10, 25, 50] as const;

function loadCache(): { query: string; data: SearchResponse } | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function saveCache(query: string, data: SearchResponse) {
  if (typeof window === "undefined") return;
  try { window.sessionStorage.setItem(CACHE_KEY, JSON.stringify({ query, data })); } catch {}
}

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
  const [limit, setLimit] = useState<number>(25);
  const reqId = useRef(0);

  useEffect(() => {
    setRecent(loadRecent());
    // Sayfa geri gelindiğinde son arama sonuçlarını geri yükle
    const cached = loadCache();
    if (cached) {
      setQuery(cached.query);
      setData(cached.data);
    }
  }, []);

  const runSearch = useCallback(async (q: string, lim?: number, forceRefresh = false) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    const id = ++reqId.current;
    setLoading(true);
    setError(null);
    setSelectedIdx(null);
    setActiveSegment(null);
    if (forceRefresh) {
      try { window.sessionStorage.removeItem(CACHE_KEY); } catch {}
    }
    try {
      const res = await searchApi.run(trimmed, lim ?? limit, forceRefresh);
      if (id !== reqId.current) return;
      setData(res);
      saveCache(trimmed, res);
      saveRecent(trimmed);
      setRecent(loadRecent());
    } catch (e) {
      if (id !== reqId.current) return;
      setError(e instanceof Error ? e.message : "Arama başarısız");
      setData(null);
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  }, [limit]);

  const handleSubmit = () => runSearch(query);
  const handleExample = (q: string) => { setQuery(q); runSearch(q); };
  const handleLimitChange = (n: number) => { setLimit(n); if (data) runSearch(query, n); };
  const handleForceRefresh = () => runSearch(query, undefined, true);

  const filtered = useMemo(() => {
    if (!data) return [];
    if (!activeSegment) return data.results.map((r, i) => ({ r, i }));
    return data.results.map((r, i) => ({ r, i })).filter(({ r }) => r.segment === activeSegment);
  }, [data, activeSegment]);

  const parsed = data?.parsed;

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex-1 min-w-0">
          <SearchInput
            value={query}
            loading={loading}
            onChange={setQuery}
            onSubmit={handleSubmit}
            onPickExample={handleExample}
          />
        </div>
        <div className="flex items-center gap-1.5 pt-[3px] shrink-0">
          <span className="font-mono text-[11px] text-dim tracking-[0.2em] uppercase">Limit:</span>
          {LIMIT_OPTIONS.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => handleLimitChange(n)}
              className={`font-mono text-[11px] px-2.5 py-1 border transition-all ${
                limit === n
                  ? "border-accent text-accent bg-accent/5"
                  : "border-stroke text-muted hover:border-accent hover:text-bright"
              }`}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {/* Recent searches */}
      {!data && !loading && recent.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[11px] text-dim tracking-[0.2em] uppercase">Son aramalar:</span>
          {recent.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => handleExample(q)}
              className="font-mono text-[11px] px-2.5 py-1 border border-stroke text-muted hover:border-accent hover:text-bright transition-all"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="border border-hot/40 bg-hot/5 px-4 py-3 font-mono text-[13px] text-hot">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!data && !loading && !error && (
        <div className="border border-dashed border-stroke p-10 text-center">
          <p className="font-mono text-[13px] text-dim tracking-wider">
            Ne tür bir firma bulmak istediğini doğal dilde yaz.
            Sonuçlar haritada gösterilir, skor ve segmente göre sıralanır.
          </p>
        </div>
      )}

      {data && (
        <>
          {/* Parsed query tags */}
          {parsed && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <span className="font-mono text-[11px] text-dim tracking-[0.2em] uppercase">Yorumlanan:</span>
              {parsed.city && <Tag k="Şehir" v={parsed.city} />}
              {parsed.district && <Tag k="İlçe" v={parsed.district} />}
              {parsed.sector && <Tag k="Sektör" v={parsed.sector} />}
              {parsed.sub_sector_hint && <Tag k="Alt" v={parsed.sub_sector_hint} />}
              <Tag k="Arama" v={parsed.search_string} />
            </div>
          )}

          <div className="flex items-center justify-between gap-3">
            <SummaryBar summary={data.summary} active={activeSegment} onToggle={setActiveSegment} />
            <button
              type="button"
              onClick={handleForceRefresh}
              disabled={loading}
              title="Cache'i atla, sıfırdan ara"
              className={`shrink-0 inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider px-2.5 py-1 border transition-all disabled:opacity-40 ${
                data.cache_hit
                  ? "border-accent/60 text-accent hover:bg-accent/10 animate-pulse"
                  : "border-stroke text-muted hover:border-stroke-2 hover:text-bright"
              }`}
            >
              <RefreshCw className="h-3 w-3" />
              {data.cache_hit ? "Önbellekten" : "Yenile"}
            </button>
          </div>

          {data.results.length === 0 ? (
            <div className="border border-dashed border-stroke p-10 text-center">
              <p className="font-mono text-[13px] text-dim">{data.error || "Sonuç bulunamadı."}</p>
              <p className="font-mono text-[12px] text-dim/60 mt-2">
                Arama terimini sadeleştirmeyi dene veya şehir/ilçe ekle.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
              <div className="lg:col-span-2 space-y-2 lg:max-h-[calc(100vh-340px)] lg:overflow-y-auto pr-1">
                {filtered.length === 0 ? (
                  <p className="font-mono text-[12px] text-dim px-1 py-4">Bu segmentte sonuç yok.</p>
                ) : (
                  filtered.map(({ r, i }) => (
                    <ResultCard
                      key={`${r.name}-${i}`}
                      lead={r}
                      selected={selectedIdx === i}
                      onSelect={() => setSelectedIdx(selectedIdx === i ? null : i)}
                      sector={parsed?.sector}
                      city={parsed?.city}
                      district={parsed?.district}
                    />
                  ))
                )}
              </div>
              <div className="lg:col-span-3 lg:sticky lg:top-4 lg:h-[calc(100vh-340px)]">
                <MapView results={data.results} selectedIdx={selectedIdx} onSelect={setSelectedIdx} />
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
    <span className="inline-flex items-center gap-1.5 font-mono text-[12px]">
      <span className="text-dim">{k}:</span>
      <span className="text-accent">{v}</span>
    </span>
  );
}
