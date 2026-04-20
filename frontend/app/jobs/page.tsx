"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { formatDateTime } from "@/lib/utils";
import { jobsApi, leadsApi } from "@/lib/api";
import type { Job, Lead } from "@/types";

const SECTOR_LABELS: Record<string, string> = {
  klinik:           "Klinik",
  avukat:           "Avukat",
  emlak:            "Emlak",
  guzellik:         "Güzellik",
  egitim:           "Eğitim",
  ev_hizmetleri:    "Tesisat / Elektrik",
  kadin_dogum:      "Kadın Doğum",
  restoran:         "Restoran",
  oto_servis:       "Oto Servis",
  klima_beyaz_esya: "Klima / Beyaz Eşya",
  cilingir:         "Çilingir",
  tadilat:          "Tadilat",
  nakliyat:         "Nakliyat",
  hali_temizlik:    "Halı & Temizlik",
};

function getPriority(avg: number | undefined) {
  if (avg === undefined) return { label: "—", cls: "text-dim border-dim/40" };
  if (avg >= 65) return { label: "Yüksek", cls: "text-hot border-hot/50 bg-hot/5" };
  if (avg >= 45) return { label: "Orta",   cls: "text-warm border-warm/50 bg-warm/5" };
  return               { label: "Düşük",   cls: "text-dim border-dim/40" };
}

function getNextAction(saved: number, avg: number | undefined, status: string): string {
  if (status === "running") return "Taranıyor...";
  if (status === "failed")  return "Hata oluştu";
  if (saved === 0)          return "Lead bulunamadı";
  if (avg === undefined)    return "Lead'leri incele";
  if (avg >= 65)            return "Mesaj yaz";
  if (avg >= 45)            return "Audit başlat";
  return "Gözden geçir";
}

interface LeadStats { hot: number; warm: number; yeni: number; auditHazir: number }

function computeStats(leads: Lead[]): LeadStats {
  const active = leads.filter((l) => !["Kapandi", "Soguk"].includes(l.status));
  return {
    hot:        active.filter((l) => (l.opportunity_score ?? 0) >= 70).length,
    warm:       active.filter((l) => { const s = l.opportunity_score ?? 0; return s >= 45 && s < 70; }).length,
    yeni:       leads.filter((l) => l.status === "Yeni").length,
    auditHazir: leads.filter((l) => l.status === "Audit").length,
  };
}

function StatCard({ icon, label, value, color, onClick }: {
  icon: string; label: string; value: number;
  color: string; onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex flex-col items-start gap-2 border border-stroke bg-panel p-4 hover:bg-panel-high transition-all text-left w-full"
    >
      <span className="text-xl leading-none">{icon}</span>
      <span className={`text-3xl font-mono font-bold leading-tight ${color}`}>{value}</span>
      <span className="font-mono text-[11px] text-muted tracking-[0.15em] uppercase leading-snug">{label}</span>
    </button>
  );
}

function ResultCell({ saved, avg, status }: { saved: number; avg?: number; status: string }) {
  if (status === "running") return (
    <span className="font-mono text-[12px] text-accent animate-pulse tracking-wider">Taranıyor…</span>
  );
  if (status === "failed") return (
    <span className="font-mono text-[12px] text-hot">Hata</span>
  );
  if (saved === 0) return (
    <span className="font-mono text-[12px] text-dim">Sonuç yok</span>
  );
  const p = getPriority(avg);
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono font-semibold text-bright text-sm">{saved}</span>
      <span className="font-mono text-[11px] text-dim">lead</span>
      {avg !== undefined && (
        <span className={`font-mono text-[11px] px-2 py-0.5 border tracking-wider uppercase ${p.cls}`}>
          ort. {avg}
        </span>
      )}
    </div>
  );
}

export default function OpportunitiesPage() {
  const router = useRouter();
  const [jobs,  setJobs]  = useState<Job[] | null>(null);
  const [stats, setStats] = useState<LeadStats | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [jobsData, leadsData] = await Promise.all([
        jobsApi.list(),
        leadsApi.list({ limit: 500 }),
      ]);
      setJobs(jobsData);
      setStats(computeStats(leadsData.items));
    } catch {
      setJobs([]);
      setStats({ hot: 0, warm: 0, yeni: 0, auditHazir: 0 });
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleDelete(id: string) {
    setDeleting(id);
    try {
      await jobsApi.delete(id);
      setJobs((prev) => prev?.filter((j) => j.id !== id) ?? null);
    } finally {
      setDeleting(null);
    }
  }

  const scrapeJobs = (jobs?.filter((j) => j.type === "collect_leads") ?? [])
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  return (
    <div className="flex flex-col flex-1">
      <Header title="Fırsatlar" description="Bugün hangi lead'lerle ilgilenmem gerekiyor?" />
      <div className="p-4 md:p-6 space-y-6">

        {/* Stat Cards */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-stroke border border-stroke">
            <StatCard icon="🔥" label="Sıcak Fırsat"               value={stats.hot}        color="text-hot"    onClick={() => router.push("/leads")} />
            <StatCard icon="💛" label="Orta Fırsat"                 value={stats.warm}       color="text-warm"   onClick={() => router.push("/leads")} />
            <StatCard icon="🆕" label="Henüz İşlenmemiş"           value={stats.yeni}       color="text-accent" onClick={() => router.push("/leads")} />
            <StatCard icon="📋" label="Audit Hazır, Mesaj Bekleyen" value={stats.auditHazir} color="text-review" onClick={() => router.push("/leads")} />
          </div>
        )}

        {/* Hot CTA */}
        {stats && stats.hot > 0 && (
          <div className="border border-hot/40 bg-hot/5 p-4 flex items-center justify-between gap-4">
            <div>
              <span className="font-mono font-semibold text-hot text-sm">
                🔥 {stats.hot} sıcak fırsat hazır
              </span>
              <span className="font-mono text-[13px] text-muted ml-3">— mesaj göndermek için doğru an</span>
            </div>
            <button
              type="button"
              onClick={() => router.push("/leads")}
              className="font-mono text-[11px] uppercase tracking-wider px-4 py-1.5 border border-hot/60 text-hot hover:bg-hot/10 transition-all whitespace-nowrap"
            >
              Lead&apos;leri Aç
            </button>
          </div>
        )}

        {/* Tarama Jobs */}
        {jobs === null ? (
          <p className="font-mono text-[13px] text-dim text-center py-10 tracking-wider">Yükleniyor…</p>
        ) : scrapeJobs.length === 0 ? (
          <div className="border border-dashed border-stroke p-12 text-center">
            <p className="font-mono text-[13px] text-dim mb-3">Henüz tarama yapılmamış.</p>
            <button
              type="button"
              onClick={() => router.push("/scrape")}
              className="font-mono text-[12px] uppercase tracking-wider text-accent hover:underline"
            >
              İlk taramayı başlat →
            </button>
          </div>
        ) : (
          <div>
            <p className="font-mono text-[11px] text-dim tracking-[0.25em] uppercase mb-3">
              ▸ Tarama Fırsatları
            </p>
            <div className="border border-stroke bg-panel overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-stroke">
                    {["Tarama", "Konum", "Sonuç", "Öncelik", "Sonraki Adım", ""].map((h, i) => (
                      <th
                        key={i}
                        className="px-4 py-3 text-left font-mono text-[11px] text-dim uppercase tracking-[0.2em] whitespace-nowrap"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-stroke">
                  {scrapeJobs.map((job) => {
                    const city     = job.payload?.city     as string | undefined;
                    const district = job.payload?.district as string | undefined;
                    const sector   = job.payload?.sector   as string | undefined;
                    const saved    = (job.result?.saved    as number | undefined) ?? 0;
                    const avg      = job.result?.avg_score as number | undefined;
                    const priority = getPriority(avg);
                    const next     = getNextAction(saved, avg, job.status);

                    return (
                      <tr key={job.id} className="hover:bg-panel-high transition-colors">
                        <td className="px-4 py-3.5">
                          <span className="font-medium text-bright text-sm">
                            {SECTOR_LABELS[sector ?? ""] ?? sector ?? "—"}
                          </span>
                          <p className="font-mono text-[12px] text-dim mt-0.5">
                            {formatDateTime(job.started_at ?? job.created_at)}
                          </p>
                        </td>
                        <td className="px-4 py-3.5 font-mono text-[13px] text-muted whitespace-nowrap">
                          {city ?? "—"}{district ? ` / ${district}` : ""}
                        </td>
                        <td className="px-4 py-3.5">
                          <ResultCell saved={saved} avg={avg} status={job.status} />
                        </td>
                        <td className="px-4 py-3.5">
                          {job.status === "running" ? (
                            <span className="font-mono text-[11px] uppercase tracking-wider px-2 py-0.5 border border-accent/50 text-accent bg-accent/5">
                              Devam ediyor
                            </span>
                          ) : job.status === "failed" ? (
                            <span className="font-mono text-[11px] uppercase tracking-wider px-2 py-0.5 border border-hot/50 text-hot bg-hot/5">
                              Başarısız
                            </span>
                          ) : (
                            <span className={`font-mono text-[11px] uppercase tracking-wider px-2 py-0.5 border ${priority.cls}`}>
                              {priority.label}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3.5">
                          {job.status === "failed" && job.error_message ? (
                            <span className="font-mono text-[12px] text-hot" title={job.error_message}>
                              {job.error_message.slice(0, 45)}{job.error_message.length > 45 ? "…" : ""}
                            </span>
                          ) : (
                            <span className="font-mono text-[13px] text-muted">{next}</span>
                          )}
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2 justify-end">
                            {job.status === "completed" && saved > 0 && (
                              <button
                                type="button"
                                onClick={() => {
                                  if (!sector) return;
                                  const q = new URLSearchParams({ sector });
                                  if (city) q.set("city", city);
                                  if (district) q.set("district", district);
                                  router.push(`/leads?${q.toString()}`);
                                }}
                                className="font-mono text-[11px] uppercase tracking-wider px-3 py-1.5 border border-accent/50 text-accent hover:bg-accent/10 transition-all whitespace-nowrap"
                              >
                                Lead&apos;leri Gör
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => handleDelete(job.id)}
                              disabled={deleting === job.id}
                              className="font-mono text-[12px] text-dim hover:text-hot disabled:opacity-40 transition-colors p-1"
                              title="Kaldır"
                            >
                              {deleting === job.id ? "…" : "✕"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
