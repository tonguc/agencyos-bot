"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { formatDateTime } from "@/lib/utils";
import { jobsApi, leadsApi } from "@/lib/api";
import type { Job, Lead } from "@/types";

// ── Helpers ──────────────────────────────────────────────────────────────────

const SECTOR_LABELS: Record<string, string> = {
  klinik: "Klinik", avukat: "Avukat", emlak: "Emlak",
  guzellik: "Güzellik", egitim: "Eğitim",
  ev_hizmetleri: "Ev Hizmetleri", kadin_dogum: "Kadın Doğum",
  restoran: "Restoran",
};

function getPriority(avg: number | undefined) {
  if (avg === undefined) return { label: "—", cls: "bg-slate-100 text-slate-400" };
  if (avg >= 65) return { label: "Yüksek", cls: "bg-red-100 text-red-700 font-semibold" };
  if (avg >= 45) return { label: "Orta",   cls: "bg-amber-100 text-amber-700 font-semibold" };
  return               { label: "Düşük",   cls: "bg-slate-100 text-slate-500" };
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

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({ icon, label, value, color, onClick }: {
  icon: string; label: string; value: number;
  color: string; onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex flex-col items-start gap-1 rounded-xl border border-slate-200 p-4 bg-white shadow-sm hover:shadow-md hover:border-slate-300 transition-all text-left w-full"
    >
      <span className="text-xl leading-none">{icon}</span>
      <span className={`text-3xl font-bold leading-tight ${color}`}>{value}</span>
      <span className="text-xs text-slate-500 leading-snug">{label}</span>
    </button>
  );
}

function ResultCell({ saved, avg, status }: { saved: number; avg?: number; status: string }) {
  if (status === "running") return <span className="text-xs text-blue-500 animate-pulse">Taranıyor…</span>;
  if (status === "failed")  return <span className="text-xs text-red-500">Hata</span>;
  if (saved === 0)           return <span className="text-xs text-slate-400">Sonuç yok</span>;
  const p = getPriority(avg);
  return (
    <div className="flex items-center gap-2">
      <span className="font-semibold text-slate-800">{saved}</span>
      <span className="text-slate-400 text-xs">lead</span>
      {avg !== undefined && (
        <span className={`text-xs px-1.5 py-0.5 rounded-full ${p.cls}`}>ort. {avg}</span>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

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

  const scrapeJobs = jobs?.filter((j) => j.type === "collect_leads") ?? [];

  return (
    <div className="flex flex-col flex-1">
      <Header
        title="Fırsatlar"
        description="Bugün hangi lead'lerle ilgilenmem gerekiyor?"
      />
      <div className="p-6 space-y-6">

        {/* ── Stat Cards ── */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard icon="🔥" label="Sıcak Fırsat"        value={stats.hot}        color="text-red-600"    onClick={() => router.push("/leads")} />
            <StatCard icon="💛" label="Orta Fırsat"          value={stats.warm}       color="text-amber-500"  onClick={() => router.push("/leads")} />
            <StatCard icon="🆕" label="Henüz İşlenmemiş"    value={stats.yeni}       color="text-blue-600"   onClick={() => router.push("/leads")} />
            <StatCard icon="📋" label="Audit Hazır, Mesaj Bekleyen" value={stats.auditHazir} color="text-violet-600" onClick={() => router.push("/leads")} />
          </div>
        )}

        {/* ── CTA Bar (yalnızca sıcak fırsat varsa) ── */}
        {stats && stats.hot > 0 && (
          <div className="rounded-xl bg-red-50 border border-red-200 p-4 flex items-center justify-between gap-4">
            <div>
              <span className="font-semibold text-red-700">🔥 {stats.hot} sıcak fırsat hazır</span>
              <span className="text-sm text-red-500 ml-2">— mesaj göndermek için doğru an</span>
            </div>
            <button
              type="button"
              onClick={() => router.push("/leads")}
              className="shrink-0 text-sm font-medium text-white bg-red-600 hover:bg-red-700 px-4 py-1.5 rounded-lg transition-colors"
            >
              Lead'leri Aç
            </button>
          </div>
        )}

        {/* ── Tarama Fırsatları ── */}
        {jobs === null ? (
          <p className="text-sm text-slate-400 text-center py-10">Yükleniyor…</p>
        ) : scrapeJobs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 p-12 text-center">
            <p className="text-sm text-slate-400 mb-3">Henüz tarama yapılmamış.</p>
            <button
              type="button"
              onClick={() => router.push("/scrape")}
              className="text-sm font-medium text-blue-600 hover:underline"
            >
              İlk taramayı başlat →
            </button>
          </div>
        ) : (
          <div>
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2 px-1">
              Tarama Fırsatları
            </h2>
            <div className="overflow-auto rounded-xl border border-slate-200 bg-white">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    {["Tarama", "Konum", "Sonuç", "Öncelik", "Sonraki Adım", ""].map((h, i) => (
                      <th key={i} className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {scrapeJobs.map((job) => {
                    const city     = job.payload?.city     as string | undefined;
                    const district = job.payload?.district as string | undefined;
                    const sector   = job.payload?.sector   as string | undefined;
                    const saved    = (job.result?.saved    as number | undefined) ?? 0;
                    const avg      = job.result?.avg_score as number | undefined;
                    const priority = getPriority(avg);
                    const next     = getNextAction(saved, avg, job.status);

                    return (
                      <tr key={job.id} className="hover:bg-slate-50/70 transition-colors">
                        {/* Tarama */}
                        <td className="px-4 py-3.5">
                          <span className="font-semibold text-slate-800">
                            {SECTOR_LABELS[sector ?? ""] ?? sector ?? "—"}
                          </span>
                          <p className="text-xs text-slate-400 mt-0.5">
                            {formatDateTime(job.started_at ?? job.created_at)}
                          </p>
                        </td>

                        {/* Konum */}
                        <td className="px-4 py-3.5 text-slate-600 whitespace-nowrap">
                          {city ?? "—"}{district ? ` / ${district}` : ""}
                        </td>

                        {/* Sonuç */}
                        <td className="px-4 py-3.5">
                          <ResultCell saved={saved} avg={avg} status={job.status} />
                        </td>

                        {/* Öncelik */}
                        <td className="px-4 py-3.5">
                          {job.status === "running" ? (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-600">Devam ediyor</span>
                          ) : job.status === "failed" ? (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600">Başarısız</span>
                          ) : (
                            <span className={`text-xs px-2 py-0.5 rounded-full ${priority.cls}`}>
                              {priority.label}
                            </span>
                          )}
                        </td>

                        {/* Sonraki Adım */}
                        <td className="px-4 py-3.5">
                          {job.status === "failed" && job.error_message ? (
                            <span className="text-xs text-red-500 font-mono" title={job.error_message}>
                              {job.error_message.slice(0, 45)}{job.error_message.length > 45 ? "…" : ""}
                            </span>
                          ) : (
                            <span className="text-sm text-slate-600">{next}</span>
                          )}
                        </td>

                        {/* İşlemler */}
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2 justify-end">
                            {job.status === "completed" && saved > 0 && (
                              <button
                                type="button"
                                onClick={() => { if (sector) router.push(`/leads?sector=${sector}`); }}
                                className="text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors"
                              >
                                Lead'leri Gör
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => handleDelete(job.id)}
                              disabled={deleting === job.id}
                              className="text-slate-300 hover:text-red-400 disabled:opacity-40 transition-colors p-1 rounded"
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
