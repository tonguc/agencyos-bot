import { Header } from "@/components/layout/header";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import type { Lead } from "@/types";
import Link from "next/link";

async function getLeads(status?: string) {
  const q = status ? `?status=${status}&limit=50` : "?limit=50";
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/leads${q}`,
      {
        headers: { "X-API-Key": process.env.NEXT_PUBLIC_API_KEY ?? "changeme" },
        cache: "no-store",
      }
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

interface Props {
  searchParams: Promise<{ status?: string }>;
}

export default async function LeadsPage({ searchParams }: Props) {
  const params = await searchParams;
  const data = await getLeads(params.status);
  const leads: Lead[] = data?.items ?? [];

  return (
    <div className="flex flex-col flex-1">
      <Header
        title="Lead'ler"
        description={params.status ? `Filtre: ${params.status}` : "Tüm lead'ler"}
      />

      <div className="p-6">
        {!data && (
          <p className="text-sm text-slate-400 text-center py-10">
            API'ye bağlanılamadı.
          </p>
        )}

        {data && leads.length === 0 && (
          <p className="text-sm text-slate-400 text-center py-10">
            Lead bulunamadı.
          </p>
        )}

        {leads.length > 0 && (
          <div className="overflow-auto rounded-xl border border-slate-200 bg-white">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">İsim</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Sektör</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Şehir</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Puan</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Durum</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Tarih</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <Link
                        href={`/leads/${lead.id}`}
                        className="font-medium text-slate-900 hover:text-blue-600"
                      >
                        {lead.name}
                      </Link>
                      {lead.phone && (
                        <p className="text-xs text-slate-400 mt-0.5">{lead.phone}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{lead.sector}</td>
                    <td className="px-4 py-3 text-slate-600">{lead.city}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {lead.google_rating ? (
                        <span>⭐ {lead.google_rating} ({lead.review_count})</span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <Badge value={lead.status} />
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{formatDate(lead.created_at)}</td>
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
