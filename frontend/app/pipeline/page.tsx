import { Header } from "@/components/layout/header";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import type { Lead } from "@/types";
import { HotLeads } from "./hot-leads";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const KEY = process.env.NEXT_PUBLIC_API_KEY ?? "changeme";
const hdrs = { "X-API-Key": KEY };

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

async function getPipelineCounts() {
  try {
    const r = await fetch(`${API}/api/leads/pipeline`, { headers: hdrs, cache: "no-store" });
    if (!r.ok) return null;
    const d = await r.json();
    return d.counts as Record<string, number>;
  } catch { return null; }
}

async function getHotLeads(): Promise<Lead[]> {
  try {
    const r = await fetch(`${API}/api/leads?status=Yeni&limit=5`, { headers: hdrs, cache: "no-store" });
    if (!r.ok) return [];
    const d = await r.json();
    const items: Lead[] = d.items ?? [];
    return items
      .filter((l) => (l.opportunity_score ?? 0) > 0)
      .sort((a, b) => (b.opportunity_score ?? 0) - (a.opportunity_score ?? 0))
      .slice(0, 5);
  } catch { return []; }
}

export default async function PipelinePage() {
  const [counts, hotLeads] = await Promise.all([getPipelineCounts(), getHotLeads()]);
  const total = counts ? Object.values(counts).reduce((s, n) => s + n, 0) : 0;

  return (
    <div className="flex flex-col flex-1">
      <Header
        title="Pipeline"
        description={counts ? `${total} kayıt · sync: şimdi` : "API bağlantısı bekleniyor"}
      />

      <div className="p-6 space-y-6">
        {!counts && (
          <p className="font-mono text-[13px] text-dim text-center py-10 tracking-wider">
            API&apos;ye bağlanılamadı. Backend çalışıyor mu?
          </p>
        )}

        {counts && (
          <>
            {/* Stage summary */}
            <div>
              <p className="font-mono text-[11px] text-dim tracking-[0.25em] uppercase mb-3">
                ▸ Pipeline Durumu
              </p>
              <div
                className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-stroke border border-stroke"
              >
                {STAGES.map(({ name, color }) => {
                  const count = counts[name] ?? 0;
                  const pct = total > 0 ? (count / total) * 100 : 0;
                  return (
                    <Link key={name} href={`/leads?status=${name}`}>
                      <div className="bg-panel hover:bg-panel-high transition-all p-4 cursor-pointer relative group">
                        <div
                          className="absolute bottom-0 left-0 right-0 h-0.5"
                          style={{ background: color, width: `${pct}%`, boxShadow: `0 0 6px ${color}` }}
                        />
                        <Badge value={name} className="mb-3" />
                        <p
                          className="text-3xl font-mono font-bold"
                          style={{ color }}
                        >
                          {count}
                        </p>
                        <p className="font-mono text-[11px] text-dim mt-1 tracking-wider">
                          {pct.toFixed(0)}% toplam
                        </p>
                      </div>
                    </Link>
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
