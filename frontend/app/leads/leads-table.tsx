"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { leadsApi, auditApi } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";
import type { Lead } from "@/types";

const SECTOR_LABELS: Record<string, string> = {
  klinik:           "Klinik / Muayenehane",
  avukat:           "Avukat / Hukuk Bürosu",
  emlak:            "Emlak / Gayrimenkul",
  guzellik:         "Güzellik / Kuaför",
  egitim:           "Eğitim / Kurs",
  ev_hizmetleri:    "Tesisat / Elektrik / Kombi",
  kadin_dogum:      "Kadın Doğum Uzmanı",
  restoran:         "Restoran / Lokanta",
  oto_servis:       "Oto Servis / Tamir",
  klima_beyaz_esya: "Klima / Beyaz Eşya / Kombi",
  cilingir:         "Çilingir / Kilitçi",
  tadilat:          "Tadilat / Boya Badana",
  nakliyat:         "Nakliyat / Evden Eve",
  hali_temizlik:    "Halı Yıkama / Ev Temizliği",
};

const PIPELINE_STATUSES = ["Yeni", "Audit", "Mesaj", "Cevap", "Demo", "Teklif", "Kapandi", "Soguk"];

const STATUS_DISPLAY: Record<string, string> = {
  Kapandi: "Kapandı",
  Soguk:   "Soğuk",
};

type SortKey = "score" | "date_desc" | "date_asc" | "name" | "google";

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "score",     label: "Skor ↓"   },
  { key: "date_desc", label: "Yeni ↓"   },
  { key: "date_asc",  label: "Eski ↑"   },
  { key: "google",    label: "Google ↓" },
  { key: "name",      label: "İsim A–Z" },
];

function sortLeads(leads: Lead[], key: SortKey): Lead[] {
  return [...leads].sort((a, b) => {
    switch (key) {
      case "score":
        return (b.opportunity_score ?? -1) - (a.opportunity_score ?? -1);
      case "date_desc":
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      case "date_asc":
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      case "google":
        return (b.google_rating ?? -1) - (a.google_rating ?? -1);
      case "name":
        return a.name.localeCompare(b.name, "tr");
    }
  });
}

function scoreStyle(v: number) {
  if (v >= 65) return "text-hot";
  if (v >= 45) return "text-warm";
  return "text-dim";
}

export function LeadsTable() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlSector   = searchParams.get("sector")   ?? "";
  const urlCity     = searchParams.get("city")     ?? "";
  const urlDistrict = searchParams.get("district") ?? "";

  const [leads,         setLeads]         = useState<Lead[]>([]);
  const [loading,       setLoading]       = useState(true);
  const [search,        setSearch]        = useState("");
  const [searchInput,   setSearchInput]   = useState("");
  const [highScoreOnly, setHighScoreOnly] = useState(false);
  const [sortKey,       setSortKey]       = useState<SortKey>("score");
  const [openSectors,   setOpenSectors]   = useState<Set<string>>(
    urlSector ? new Set([urlSector]) : new Set()
  );
  const [auditingId,     setAuditingId]     = useState<string | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState<string | null>(null);
  const [deletingId,     setDeletingId]     = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await leadsApi.list({
        limit:    500,
        sector:   urlSector   || undefined,
        city:     urlCity     || undefined,
        district: urlDistrict || undefined,
        search:   search      || undefined,
      });
      setLeads(data.items);
      // Open all sector groups by default so leads are visible without extra clicks
      if (data.items.length > 0) {
        setOpenSectors(new Set(data.items.map((l) => l.sector)));
      }
    } catch {
      setLeads([]);
    } finally {
      setLoading(false);
    }
  }, [search, urlSector, urlCity, urlDistrict]);

  function clearLocationFilter() {
    const q = new URLSearchParams(searchParams.toString());
    q.delete("city");
    q.delete("district");
    router.push(`/leads${q.toString() ? `?${q.toString()}` : ""}`);
  }

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

  // Sector groups sorted by latest lead date desc
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
    <div className="p-4 md:p-6 space-y-4">

      {/* Filters + Sort */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 flex-wrap">
        <Input
          className="w-full sm:w-64"
          placeholder="İsim veya şehir ara..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />

        {/* Sort buttons */}
        <div className="flex items-center gap-1 flex-wrap">
          {SORT_OPTIONS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => setSortKey(key)}
              className={`px-2.5 py-1 text-[11px] font-mono tracking-[0.15em] uppercase border transition-all ${
                sortKey === key
                  ? "bg-accent/10 border-accent text-accent"
                  : "border-stroke text-dim hover:border-stroke-2 hover:text-muted"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setHighScoreOnly((v) => !v)}
          className={`px-3 py-1 text-[11px] font-mono tracking-[0.2em] uppercase border transition-all ${
            highScoreOnly
              ? "bg-hot/10 text-hot border-hot/60"
              : "border-stroke text-dim hover:border-stroke-2 hover:text-muted"
          }`}
        >
          Yüksek Skor 70+
        </button>

        {(urlCity || urlDistrict) && (
          <button
            type="button"
            onClick={clearLocationFilter}
            className="flex items-center gap-1.5 px-3 py-1 text-[11px] font-mono tracking-[0.2em] uppercase border border-accent/60 bg-accent/10 text-accent hover:bg-accent/20 transition-all"
          >
            <span>📍 {urlCity}{urlDistrict ? ` / ${urlDistrict}` : ""}</span>
            <span className="text-accent/60">✕</span>
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner className="text-muted h-5 w-5" />
        </div>
      ) : sectors.length === 0 ? (
        <p className="font-mono text-[13px] text-dim text-center py-16 tracking-wider">
          Aday bulunamadı.
        </p>
      ) : (
        <div className="space-y-3">
          {sectors.map(([sector, items]) => {
            const isOpen   = openSectors.has(sector);
            const label    = SECTOR_LABELS[sector] ?? sector;
            const sorted   = sortLeads(items, sortKey);
            const latestAt = Math.max(...items.map((l) => new Date(l.created_at).getTime()));
            const scrapeDate = formatDate(new Date(latestAt).toISOString());
            const avgScore = items.reduce((s, l) => s + (l.opportunity_score ?? 0), 0) / items.length;

            return (
              <div key={sector} className="border border-stroke bg-panel overflow-hidden">

                {/* Sector header */}
                <button
                  type="button"
                  onClick={() => toggleSector(sector)}
                  className="w-full flex items-center justify-between px-5 py-3.5 bg-panel-high hover:bg-stroke/30 transition-colors border-b border-stroke"
                >
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="font-mono font-bold text-bright text-xs tracking-wider uppercase">
                      {label}
                    </span>
                    <span className="font-mono text-[11px] border border-stroke-2 text-muted px-2 py-0.5 tracking-wider">
                      {items.length} ADAY
                    </span>
                    <span className="font-mono text-[11px] text-dim tracking-wider">
                      ort. <span className={`font-semibold ${scoreStyle(avgScore)}`}>{avgScore.toFixed(0)}</span>
                    </span>
                    <span className="font-mono text-[11px] text-dim tracking-wider">
                      · Son tarama: <span className="text-muted">{scrapeDate}</span>
                    </span>
                  </div>
                  <span className="font-mono text-[11px] text-dim tracking-wider shrink-0">
                    {isOpen ? "KAPAT ▲" : "GÖSTER ▼"}
                  </span>
                </button>

                {isOpen && (
                  <div className="overflow-x-auto -webkit-overflow-scrolling-touch">
                    <table className="min-w-full">
                      <thead>
                        <tr className="border-b border-stroke">
                          {["İsim", "Şehir / İlçe", "Google", "Skor", "Durum", "Tarama Tarihi", "", ""].map((h, i) => (
                            <th
                              key={i}
                              className="px-4 py-2.5 text-left font-mono text-[11px] text-dim uppercase tracking-[0.2em] whitespace-nowrap"
                            >
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-stroke">
                        {sorted.map((lead) => (
                          <tr
                            key={lead.id}
                            onClick={() => router.push(`/leads/${lead.id}`)}
                            className="hover:bg-panel-high cursor-pointer transition-colors"
                          >
                            <td className="px-4 py-3">
                              <span className="font-medium text-bright text-sm">{lead.name}</span>
                              {lead.phone && (
                                <p className="font-mono text-[12px] text-dim mt-0.5">{lead.phone}</p>
                              )}
                            </td>
                            <td className="px-4 py-3 font-mono text-[13px] text-muted whitespace-nowrap">
                              {lead.city}{lead.district ? ` / ${lead.district}` : ""}
                            </td>
                            <td className="px-4 py-3 font-mono text-[13px] text-muted whitespace-nowrap">
                              {lead.google_rating
                                ? `⭐ ${lead.google_rating} (${lead.review_count})`
                                : "—"}
                            </td>
                            <td className="px-4 py-3">
                              {lead.opportunity_score != null ? (
                                <span className={`font-mono font-bold text-sm ${scoreStyle(lead.opportunity_score)}`}>
                                  {lead.opportunity_score}
                                </span>
                              ) : (
                                <span className="text-dim font-mono">—</span>
                              )}
                            </td>
                            <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                              <select
                                value={lead.status}
                                onChange={(e) => handleStatusChange(e, lead)}
                                disabled={updatingStatus === lead.id}
                                className="font-mono text-[11px] border border-stroke px-2 py-1 tracking-wider uppercase cursor-pointer focus:outline-none focus:border-accent disabled:opacity-50"
                                style={{ background: "#0d1324", color: "#7a8aa8" }}
                              >
                                {PIPELINE_STATUSES.map((s) => (
                                  <option key={s} value={s}>{STATUS_DISPLAY[s] ?? s}</option>
                                ))}
                              </select>
                            </td>
                            <td className="px-4 py-3 font-mono text-[12px] text-dim whitespace-nowrap">
                              {formatDate(lead.created_at)}
                            </td>
                            <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                              <button
                                onClick={(e) => handleAudit(e, lead.id)}
                                disabled={auditingId === lead.id}
                                className="font-mono text-[11px] uppercase tracking-wider px-2.5 py-1 border border-accent/50 text-accent hover:bg-accent/10 disabled:opacity-40 transition-all whitespace-nowrap"
                              >
                                {auditingId === lead.id ? "..." : "Audit Başlat"}
                              </button>
                            </td>
                            <td className="px-3 py-3" onClick={(e) => e.stopPropagation()}>
                              <button
                                onClick={(e) => handleDelete(e, lead.id)}
                                disabled={deletingId === lead.id}
                                className="font-mono text-[12px] text-dim hover:text-hot disabled:opacity-40 transition-colors p-1"
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
