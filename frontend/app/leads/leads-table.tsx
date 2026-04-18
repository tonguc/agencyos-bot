"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { leadsApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";
import type { Lead } from "@/types";

const SECTOR_LABELS: Record<string, string> = {
  klinik: "Klinik / Muayenehane",
  diyetisyen: "Diyetisyen",
  avukat: "Avukat / Hukuk Bürosu",
  plastik_cerrah: "Plastik Cerrah / Estetik",
  kadin_dogum: "Kadın Doğum Uzmanı",
  guzellik: "Güzellik Merkezi / Botoks",
  tesisatci: "Sıhhi Tesisat",
};

export function LeadsTable() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlSector = searchParams.get("sector") ?? "";

  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [openSectors, setOpenSectors] = useState<Set<string>>(
    urlSector ? new Set([urlSector]) : new Set()
  );

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

  // group by sector, sorted by most recent lead
  const grouped = leads.reduce<Record<string, Lead[]>>((acc, lead) => {
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
      <Input
        className="w-72"
        placeholder="İsim, sektör veya şehir ara..."
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
      />

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
                {/* Sector header */}
                <button
                  type="button"
                  onClick={() => toggleSector(sector)}
                  className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-slate-800">{label}</span>
                    <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">
                      {items.length} aday
                    </span>
                  </div>
                  <span className="text-slate-400 text-sm">{isOpen ? "▲" : "▼"}</span>
                </button>

                {/* Leads table */}
                {isOpen && (
                  <div className="border-t border-slate-100 overflow-auto">
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="bg-slate-50 border-b border-slate-100">
                          {["İsim", "Şehir / İlçe", "Google", "Skor", "Durum", "Tarih"].map((h) => (
                            <th key={h} className="px-4 py-2.5 text-left text-xs font-medium text-slate-500 uppercase tracking-wide whitespace-nowrap">
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
                            <td className="px-4 py-3"><Badge value={lead.status} /></td>
                            <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">{formatDate(lead.created_at)}</td>
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
