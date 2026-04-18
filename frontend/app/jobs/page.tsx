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

  return (
    <div className="flex flex-col flex-1">
      <Header title="İşler" description="Arka plan görevleri" />
      <div className="p-6">
        {jobs === null && (
          <p className="text-sm text-slate-400 text-center py-10">Yükleniyor...</p>
        )}
        {jobs && jobs.length === 0 && (
          <p className="text-sm text-slate-400 text-center py-10">Henüz iş yok.</p>
        )}
        {jobs && jobs.length > 0 && (
          <div className="overflow-auto rounded-xl border border-slate-200 bg-white">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Tür</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Durum</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Şehir / İlçe</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Bulunan</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Ort. Puan</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Başlangıç</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {jobs.map((job) => {
                  const city = job.payload?.city as string | undefined;
                  const district = job.payload?.district as string | undefined;
                  const saved = job.result?.saved as number | undefined;
                  const avgScore = job.result?.avg_score as number | undefined;
                  return (
                    <tr
                      key={job.id}
                      onClick={() => {
                        const sector = job.payload?.sector as string | undefined;
                        if (job.type === "collect_leads" && sector) router.push(`/leads?sector=${sector}`);
                        else if (job.payload?.lead_id) router.push(`/leads/${job.payload.lead_id}`);
                      }}
                      className="hover:bg-blue-50 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3 font-medium text-slate-800">
                        {typeLabel[job.type] ?? job.type}
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
                        {job.started_at ? formatDateTime(job.started_at) : formatDateTime(job.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(job.id); }}
                          disabled={deleting === job.id}
                          className="text-xs text-red-500 hover:text-red-700 disabled:opacity-40"
                        >
                          {deleting === job.id ? "..." : "Sil"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
