"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "@/lib/utils";
import { jobsApi } from "@/lib/api";
import type { Job } from "@/types";

const typeLabel: Record<string, string> = {
  generate_audit: "Audit",
  generate_outreach: "Mesaj Yaz",
  generate_proposal: "Teklif Oluştur",
  collect_leads: "Aday Tarama",
};

function DeleteBtn({ job, deleting, onDelete }: {
  job: Job;
  deleting: string | null;
  onDelete: (id: string) => void;
}) {
  return (
    <td className="px-4 py-3 text-right whitespace-nowrap">
      {job.status === "failed" && job.error_message && (
        <span
          className="mr-3 text-xs text-red-500 font-mono max-w-xs truncate inline-block align-middle"
          title={job.error_message}
        >
          {job.error_message.slice(0, 50)}{job.error_message.length > 50 ? "…" : ""}
        </span>
      )}
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(job.id); }}
        disabled={deleting === job.id}
        className="text-xs text-red-500 hover:text-red-700 disabled:opacity-40"
      >
        {deleting === job.id ? "..." : "Sil"}
      </button>
    </td>
  );
}

export default function JobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await jobsApi.list();
      setJobs(data);
    } catch {
      setJobs([]);
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

  if (jobs === null) {
    return (
      <div className="flex flex-col flex-1">
        <Header title="İşler" description="Arka plan görevleri" />
        <p className="text-sm text-slate-400 text-center py-10">Yükleniyor...</p>
      </div>
    );
  }

  const scrapeJobs = jobs.filter((j) => j.type === "collect_leads");
  const processJobs = jobs.filter((j) => j.type !== "collect_leads");

  return (
    <div className="flex flex-col flex-1">
      <Header title="İşler" description="Arka plan görevleri" />
      <div className="p-6 space-y-6">
        {jobs.length === 0 && (
          <p className="text-sm text-slate-400 text-center py-10">Henüz iş yok.</p>
        )}

        {/* Aday Tarama */}
        {scrapeJobs.length > 0 && (
          <div>
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2 px-1">
              Aday Tarama
            </h2>
            <div className="overflow-auto rounded-xl border border-slate-200 bg-white">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Sektör</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Durum</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Şehir / İlçe</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Bulunan</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Ort. Puan</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Başlangıç</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {scrapeJobs.map((job) => {
                    const city = job.payload?.city as string | undefined;
                    const district = job.payload?.district as string | undefined;
                    const sector = job.payload?.sector as string | undefined;
                    const saved = job.result?.saved as number | undefined;
                    const avgScore = job.result?.avg_score as number | undefined;
                    return (
                      <tr
                        key={job.id}
                        onClick={() => { if (sector) router.push(`/leads?sector=${sector}`); }}
                        className="hover:bg-blue-50 cursor-pointer transition-colors"
                      >
                        <td className="px-4 py-3 font-medium text-slate-800 capitalize">
                          {sector ?? "—"}
                        </td>
                        <td className="px-4 py-3"><Badge value={job.status} /></td>
                        <td className="px-4 py-3 text-slate-600 text-xs">
                          {city ?? "—"}{district ? ` / ${district}` : ""}
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {saved !== undefined ? `${saved} lead` : "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {avgScore !== undefined ? avgScore : "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-400 text-xs">
                          {formatDateTime(job.started_at ?? job.created_at)}
                        </td>
                        <DeleteBtn job={job} deleting={deleting} onDelete={handleDelete} />
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Lead İşlemleri */}
        {processJobs.length > 0 && (
          <div>
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2 px-1">
              Lead İşlemleri
            </h2>
            <div className="overflow-auto rounded-xl border border-slate-200 bg-white">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">İşlem</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Durum</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Lead</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Başlangıç</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {processJobs.map((job) => {
                    const leadId = job.payload?.lead_id as string | undefined;
                    return (
                      <tr
                        key={job.id}
                        onClick={() => { if (leadId) router.push(`/leads/${leadId}`); }}
                        className="hover:bg-blue-50 cursor-pointer transition-colors"
                      >
                        <td className="px-4 py-3 font-medium text-slate-800">
                          {typeLabel[job.type] ?? job.type}
                        </td>
                        <td className="px-4 py-3"><Badge value={job.status} /></td>
                        <td className="px-4 py-3 text-slate-400 font-mono text-xs">
                          {leadId ? leadId.slice(0, 8) + "…" : "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-400 text-xs">
                          {formatDateTime(job.started_at ?? job.created_at)}
                        </td>
                        <DeleteBtn job={job} deleting={deleting} onDelete={handleDelete} />
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
