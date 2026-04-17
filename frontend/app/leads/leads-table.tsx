"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { leadsApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";
import type { Lead } from "@/types";

const STATUSES = ["", "Yeni", "Audit", "Mesaj", "Cevap", "Demo", "Teklif", "Kapandi", "Soguk"];
const PAGE_SIZE = 20;

export function LeadsTable() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [page, setPage] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await leadsApi.list({
        status: status || undefined,
        search: search || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });
      setLeads(data.items);
      setTotal(data.total);
    } catch {
      setLeads([]);
    } finally {
      setLoading(false);
    }
  }, [status, search, page]);

  useEffect(() => { load(); }, [load]);

  // debounce search
  const [searchInput, setSearchInput] = useState(search);
  useEffect(() => {
    const t = setTimeout(() => { setSearch(searchInput); setPage(0); }, 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6 space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <Input
          className="w-64"
          placeholder="İsim veya sektör ara..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <div className="flex flex-wrap gap-1.5">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => { setStatus(s); setPage(0); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                status === s
                  ? "bg-slate-900 text-white border-slate-900"
                  : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
              }`}
            >
              {s || "Tümü"}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-16"><Spinner className="text-slate-400 h-6 w-6" /></div>
      ) : leads.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-16">Lead bulunamadı.</p>
      ) : (
        <div className="overflow-auto rounded-xl border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                {["İsim", "Sektör", "Şehir", "Google", "Skor", "Durum", "Tarih", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {leads.map((lead) => (
                <tr key={lead.id} className="hover:bg-slate-50 transition-colors group">
                  <td className="px-4 py-3">
                    <Link href={`/leads/${lead.id}`} className="font-medium text-slate-900 hover:text-blue-600">
                      {lead.name}
                    </Link>
                    {lead.phone && <p className="text-xs text-slate-400 mt-0.5">{lead.phone}</p>}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{lead.sector}</td>
                  <td className="px-4 py-3 text-slate-600 whitespace-nowrap">
                    {lead.city}{lead.district ? ` / ${lead.district}` : ""}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-slate-600">
                    {lead.google_rating ? `⭐ ${lead.google_rating} (${lead.review_count})` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {lead.opportunity_score != null ? (
                      <span className={`font-bold ${lead.opportunity_score >= 70 ? "text-green-600" : lead.opportunity_score >= 40 ? "text-orange-500" : "text-slate-500"}`}>
                        {lead.opportunity_score}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3"><Badge value={lead.status} /></td>
                  <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">{formatDate(lead.created_at)}</td>
                  <td className="px-4 py-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => router.push(`/leads/${lead.id}`)}
                      className="opacity-0 group-hover:opacity-100"
                    >
                      Detay →
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <p className="text-slate-500">{total} lead · sayfa {page + 1}/{totalPages}</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
              ← Önceki
            </Button>
            <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>
              Sonraki →
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
