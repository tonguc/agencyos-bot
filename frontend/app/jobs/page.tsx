import { Header } from "@/components/layout/header";
import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "@/lib/utils";
import type { Job } from "@/types";

async function getJobs(): Promise<Job[] | null> {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/jobs?limit=100`,
      {
        headers: { "X-API-Key": process.env.NEXT_PUBLIC_API_KEY ?? "changeme" },
        cache: "no-store",
      }
    );
    return res.ok ? res.json() : null;
  } catch { return null; }
}

const typeLabel: Record<string, string> = {
  generate_audit: "Audit",
  generate_outreach: "Outreach",
  generate_proposal: "Teklif",
  collect_leads: "Lead Topla",
};

export default async function JobsPage() {
  const jobs = await getJobs();

  return (
    <div className="flex flex-col flex-1">
      <Header title="İşler" description="Arka plan görevleri" />
      <div className="p-6">
        {!jobs && (
          <p className="text-sm text-slate-400 text-center py-10">API'ye bağlanılamadı.</p>
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
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">İlerleme</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Mesaj</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Başlangıç</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-800">
                      {typeLabel[job.type] ?? job.type}
                    </td>
                    <td className="px-4 py-3"><Badge value={job.status} /></td>
                    <td className="px-4 py-3 text-slate-600">{job.progress_pct}%</td>
                    <td className="px-4 py-3 text-slate-500 text-xs max-w-xs truncate">
                      {job.error_message ?? job.progress_message ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {job.started_at ? formatDateTime(job.started_at) : formatDateTime(job.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
