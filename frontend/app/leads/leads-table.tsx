"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { leadsApi, auditApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";
import type { Lead } from "@/types";

const SECTOR_LABELS: Record<string, string> = {
  klinik: "Klinik / Muayenehane",
  avukat: "Avukat / Hukuk Bürosu",
  emlak: "Emlak / Gayrimenkul",
  guzellik: "Güzellik / Kuaför",
  egitim: "Eğitim / Kurs",
  ev_hizmetleri: "Ev Hizmetleri",
  kadin_dogum: "Kadın Doğum Uzmanı",
  restoran: "Restoran / Lokanta",
};

const PIPELINE_STATUSES = ["Yeni", "Audit", "Mesaj", "Cevap", "Demo", "Teklif", "Kapandi", "Soguk"];

export function LeadsTable() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlSector = searchParams.get("sector") ?? "";

  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [highScoreOnly, setHighScoreOnly] = useState(false);
  const [openSectors, setOpenSectors] = useState<Set<string>>(
    urlSector ? new Set([urlSector]) : new Set()
  );
  const [auditingId, setAuditingId] = useState<string | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await leadsApi.list({ limit: 500, search: search || undefined });
      setLeads(data.items);
      if (!urlSector && data.items.length > 0) {
        const latest = data.items.reduce((a, b) =>
          new Date(a.created_at) > new Date(b.created_at) ? a : b
        );
        setOpenSectors((prev) => new Set([...prev, latest.sector]));
      }
    } catch {
      setLeads([]);
    } finally {
      setLoading(false);
    }
  }, [search, urlSector]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput), 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  async function handleAudit(e: React.MouseEvent, leadId: string) {
    e.stopPropagation();
    setAuditingId(leadId);
    try {
      await auditApi.trigger(leadId);
      router.push(`/leads/${leadId}`);
    } catch {
      setAuditingId(null);
    }
  }

  async function handleDelete(e: React.MouseEvent, leadId: string) {
    e.stopPropagation();
    setDeletingId(leadId);
    try {
      await leadsApi.delete(leadId);
      setLeads((prev) => prev.filter((l) => l.id !== leadId));
    } finally {
      setDeletingId(null);
    }
  }

  async function handleStatusChange(e: React.ChangeEvent<HTMLSelectElement>, lead: Lead) {
    e.stopPropagation();
    const newStatus = e.target.value;
    setUpdatingStatus(lead.id);
    try {
      await leadsApi.update(lead.id, { status: newStatus });
      setLeads((prev) => prev.map((l) => l.id === lead.id ? { ...l, status: newStatus } : l));
    } finally {
      setUpdatingStatus(null);
    }
  }

  const filteredLeads = highScoreOnly
    ? leads.filter((l) => (l.opportunity_score ?? 0) >= 70)
    : leads;

  const grouped = filteredLeads.reduce<Record<string, Lead[]>>((acc, lead) => {
    if (!acc[lead.sector]) acc[lead.sector] = [];
    acc[lead.sector].push(lead);
    return acc;
  }, {});

  const sectors = Object.entries(grouped).sort(([, a], [, b]) => {
    const latestA = Math.max(...a.map((l) => new Date(l.created_at).getTime()));
    const latestB = Math.max(...b.map((l) => new Date(l.created_at).getTime()));
    return latestB - latestA;
  });

  function toggleSector(sector: string) {
    setOpenSectors((prev) => {
      const next = new Set(prev);
      if (next.has(sector)) next.delete(sector);
      else next.add(sector);
      return next;
    });
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <Input
          className="w-72"
          placeholder="İsim, sektör veya şehir ara..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <button
          type="button"
          onClick={() => setHighScoreOnly((v) => !v)}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
            highScoreOnly
              ? "bg-green-600 text-white border-green-600"
              : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
          }`}
        >
          Yüksek Skor (70+)
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner className="text-slate-400 h-6 w-6" /></div>
      ) : sectors.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-16">Aday bulunamadı.</p>
      ) : (
        <div className="space-y-3">
          {sectors.map(([sector, items]) => {
            const isOpen = openSectors.has(sector);
            const label = SECTOR_LABELS[sector] ?? sector;
            return (
              <div key={sector} className="rounded-xl border border-slate-200 bg-white overflow-hidden">
                <button
                  type="button"
                  onClick={() => toggleSector(sector)}
                  className="w-full flex items-center justify-between px-5 py-4 bg-slate-50 hover:bg-slate-100 transition-colors border-b border-slate-200"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-base font-bold text-slate-900 tracking-tight">{label}</span>
                    <span className="text-xs font-semibold bg-white border border-slate-200 text-slate-500 px-2.5 py-0.5 rounded-full">
                      {items.length} aday
                    </span>
                  </div>
                  <span className="text-slate-400 text-xs font-medium">{isOpen ? "Kapat ▲" : "Göster ▼"}</span>
                </button>

                {isOpen && (
                  <div className="overflow-auto">
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="bg-white border-b border-slate-100">
                          {["İsim", "Şehir / İlçe", "Google", "Skor", "Durum", "Tarih", "", ""].map((h, i) => (
                            <th key={i} className="px-4 py-2.5 text-left text-xs font-medium text-slate-400 uppercase tracking-wide whitespace-nowrap">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-50">
                        {items.map((lead) => (
                          <tr
                            key={lead.id}
                            onClick={() => router.push(`/leads/${lead.id}`)}
                            className="hover:bg-blue-50 cursor-pointer transition-colors"
                          >
                            <td className="px-4 py-3">
                              <span className="font-medium text-slate-900">{lead.name}</span>
                              {lead.phone && <p className="text-xs text-slate-400 mt-0.5">{lead.phone}</p>}
                            </td>
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
                            <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                              <select
                                value={lead.status}
                                onChange={(e) => handleStatusChange(e, lead)}
                                disabled={updatingStatus === lead.id}
                                className="text-xs border border-slate-200 rounded-md px-2 py-1 bg-white text-slate-700 cursor-pointer focus:outline-none focus:ring-1 focus:ring-blue-400 disabled:opacity-50"
                              >
                                {PIPELINE_STATUSES.map((s) => (
                                  <option key={s} value={s}>{s}</option>
                                ))}
                              </select>
                            </td>
                            <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">{formatDate(lead.created_at)}</td>
                            <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                              <button
                                onClick={(e) => handleAudit(e, lead.id)}
                                disabled={auditingId === lead.id}
                                className="text-xs px-2.5 py-1 rounded-md bg-blue-50 text-blue-600 hover:bg-blue-100 border border-blue-200 disabled:opacity-50 whitespace-nowrap"
                              >
                                {auditingId === lead.id ? "..." : "Audit Başlat"}
                              </button>
                            </td>
                            <td className="px-3 py-3" onClick={(e) => e.stopPropagation()}>
                              <button
                                onClick={(e) => handleDelete(e, lead.id)}
                                disabled={deletingId === lead.id}
                                className="text-slate-300 hover:text-red-400 disabled:opacity-40 transition-colors p-1 rounded"
                                title="Kaldır"
                              >
                                {deletingId === lead.id ? "…" : "✕"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
