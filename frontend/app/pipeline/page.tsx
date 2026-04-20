"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Badge } from "@/components/ui/badge";
import { leadsApi } from "@/lib/api";
import { HotLeads } from "./hot-leads";
import type { Lead } from "@/types";

const STAGES: { name: string; color: string }[] = [
  { name: "Yeni",    color: "#38bdf8" },
  { name: "Audit",   color: "#a774ff" },
  { name: "Mesaj",   color: "#ffb648" },
  { name: "Cevap",   color: "#fb923c" },
  { name: "Demo",    color: "#f472b6" },
  { name: "Teklif",  color: "#34d399" },
  { name: "Kapandi", color: "#34d399" },
  { name: "Soguk",   color: "#4a5876" },
];

export default function OzetPage() {
  const router = useRouter();
  const [counts, setCounts]     = useState<Record<string, number> | null>(null);
  const [hotLeads, setHotLeads] = useState<Lead[]>([]);
  const [loading, setLoading]   = useState(true);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      const [pipelineData, leadsData] = await Promise.all([
        leadsApi.pipeline(),
        leadsApi.list({ status: "Yeni", limit: 5 }),
      ]);
      setCounts(pipelineData.counts);
      const hot = (leadsData.items ?? [])
        .filter((l) => (l.opportunity_score ?? 0) > 0)
        .sort((a, b) => (b.opportunity_score ?? 0) - (a.opportunity_score ?? 0))
        .slice(0, 5);
      setHotLeads(hot);
      setUpdatedAt(new Date());
    } catch {
      setCounts({});
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const total = counts ? Object.values(counts).reduce((s, n) => s + n, 0) : 0;
  const timeStr = updatedAt
    ? updatedAt.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : "—";

  return (
    <div className="flex flex-col flex-1">
      <Header
        title="Özet"
        description={loading ? "Yükleniyor…" : `${total} kayıt · güncellendi: ${timeStr}`}
      />

      <div className="p-6 space-y-6">
        {/* Refresh button */}
        <div className="flex justify-end">
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="font-mono text-[11px] uppercase tracking-wider px-3 py-1.5 border border-stroke text-dim hover:border-accent hover:text-accent disabled:opacity-40 transition-all"
          >
            {loading ? "Yükleniyor…" : "↻ Yenile"}
          </button>
        </div>

        {counts && (
          <>
            {/* Stage summary */}
            <div>
              <p className="font-mono text-[11px] text-dim tracking-[0.25em] uppercase mb-3">
                ▸ Aşama Durumu
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-stroke border border-stroke">
                {STAGES.map(({ name, color }) => {
                  const count = counts[name] ?? 0;
                  const pct = total > 0 ? (count / total) * 100 : 0;
                  return (
                    <button
                      key={name}
                      type="button"
                      onClick={() => router.push(`/leads?status=${name}`)}
                      className="bg-panel hover:bg-panel-high transition-all p-4 cursor-pointer relative text-left"
                    >
                      <div
                        className="absolute bottom-0 left-0 h-0.5"
                        style={{ background: color, width: `${pct}%`, boxShadow: `0 0 6px ${color}` }}
                      />
                      <Badge value={name} className="mb-3" />
                      <p className="text-3xl font-mono font-bold" style={{ color }}>
                        {count}
                      </p>
                      <p className="font-mono text-[11px] text-dim mt-1 tracking-wider">
                        {pct.toFixed(0)}% toplam
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Hot leads */}
            <HotLeads initial={hotLeads} />
          </>
        )}
      </div>
    </div>
  );
}
