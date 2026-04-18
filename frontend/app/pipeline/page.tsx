import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import type { Lead } from "@/types";
import { HotLeads } from "./hot-leads";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const KEY = process.env.NEXT_PUBLIC_API_KEY ?? "changeme";
const hdrs = { "X-API-Key": KEY };

const STAGES: { name: string; color: string }[] = [
  { name: "Yeni",     color: "border-l-blue-400" },
  { name: "Audit",    color: "border-l-violet-400" },
  { name: "Mesaj",    color: "border-l-yellow-400" },
  { name: "Cevap",    color: "border-l-orange-400" },
  { name: "Demo",     color: "border-l-pink-400" },
  { name: "Teklif",   color: "border-l-emerald-400" },
  { name: "Kapandi",  color: "border-l-green-500" },
  { name: "Soguk",    color: "border-l-slate-300" },
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
        description={counts ? `Toplam ${total} lead` : "Lead pipeline"}
      />

      <div className="p-6 space-y-6">
        {!counts && (
          <p className="text-sm text-slate-400 text-center py-10">API'ye bağlanılamadı. Backend çalışıyor mu?</p>
        )}

        {/* Stage cards */}
        {counts && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {STAGES.map(({ name, color }) => {
              const count = counts[name] ?? 0;
              return (
                <Link key={name} href={`/leads?status=${name}`}>
                  <Card className={`border-l-4 ${color} hover:shadow-md transition-all cursor-pointer`}>
                    <CardContent className="p-4">
                      <Badge value={name} className="mb-2" />
                      <p className="text-2xl font-bold text-slate-900">{count}</p>
                      <div className="mt-2 h-1 w-full rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-slate-300"
                          style={{ width: total > 0 ? `${(count / total) * 100}%` : "0%" }}
                        />
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}

        {/* Hot leads */}
        <HotLeads initial={hotLeads} />
      </div>
    </div>
  );
}
