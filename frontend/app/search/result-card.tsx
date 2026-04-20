"use client";

import { useState } from "react";
import { ExternalLink, Globe, MapPin, MessageSquare, Phone } from "lucide-react";
import { useRouter } from "next/navigation";
import type { SearchResultItem } from "@/types";
import { leadsApi } from "@/lib/api";
import { SEGMENT_COLORS, SEGMENT_LABELS } from "./segment";

interface Props {
  lead: SearchResultItem;
  selected: boolean;
  onSelect: () => void;
  sector?: string | null;
  city?: string | null;
  district?: string | null;
}

function whatsappLink(phone: string | null): string | null {
  if (!phone) return null;
  const digits = phone.replace(/\D/g, "");
  return digits ? `https://wa.me/${digits}` : null;
}

function signalIcon(s: string): string {
  if (s.startsWith("+") || s.match(/^Elendi/)) return "▲";
  if (s.startsWith("-")) return "▼";
  return "•";
}

function signalColor(s: string): string {
  if (s.startsWith("+")) return "text-ok";
  if (s.startsWith("-")) return "text-hot";
  if (s.startsWith("Elendi")) return "text-hot";
  return "text-muted";
}

export function ResultCard({ lead, selected, onSelect, sector, city, district }: Props) {
  const c = SEGMENT_COLORS[lead.segment];
  const wa = whatsappLink(lead.phone);
  const router = useRouter();
  const [saving, setSaving] = useState(false);

  async function handleClick() {
    if (lead.lead_id) {
      router.push(`/leads/${lead.lead_id}`);
      return;
    }
    // Save to DB first, then navigate to detail page
    setSaving(true);
    try {
      const created = await leadsApi.create({
        name: lead.name,
        sector: sector || "klinik",
        city: city || "bilinmiyor",
        district: district || "",
        address: lead.address || undefined,
        phone: lead.phone || undefined,
        website: lead.website || undefined,
        google_rating: lead.google_rating ?? undefined,
        review_count: lead.review_count ?? undefined,
      });
      router.push(`/leads/${created.id}`);
    } catch {
      setSaving(false);
      onSelect();
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleClick(); }
      }}
      className={`group relative border bg-panel cursor-pointer transition-all ${
        selected ? "border-stroke-2 bg-panel-high" : "border-stroke hover:border-stroke-2"
      } ${saving ? "opacity-60 pointer-events-none" : ""}`}
      style={
        selected
          ? { borderLeftWidth: "3px", borderLeftColor: c.color, boxShadow: `0 0 20px ${c.color}18` }
          : { borderLeftWidth: "3px", borderLeftColor: "#1c2742" }
      }
    >
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-bright text-sm truncate">{lead.name || "(isimsiz)"}</h3>
            <p className="mt-0.5 text-[12px] font-mono text-muted truncate tracking-wider">
              {lead.category || "—"}
            </p>
          </div>
          <div className="flex flex-col items-end shrink-0">
            <span
              className="text-[11px] font-mono font-medium uppercase tracking-[0.2em]"
              style={{ color: c.color }}
            >
              {lead.lead_id || lead.segment === "low"
                ? SEGMENT_LABELS[lead.segment]
                : "Ön Analiz"}
            </span>
            {saving && (
              <span className="text-[8px] font-mono text-accent mt-1 animate-pulse">kaydediliyor…</span>
            )}
            {!saving && (
              <span className="text-[8px] font-mono text-dim mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {lead.lead_id ? "DETAY →" : "KAYDET & AÇ →"}
              </span>
            )}
          </div>
        </div>

        <div className="mt-3 space-y-1 text-[13px] font-mono text-muted">
          {lead.address && (
            <div className="flex items-start gap-1.5">
              <MapPin className="h-3 w-3 shrink-0 mt-0.5 text-dim" />
              <span className="line-clamp-2">{lead.address}</span>
            </div>
          )}
          <div className="flex items-center gap-3 flex-wrap">
            {lead.google_rating != null && (
              <span className="text-bright">
                ⭐ {lead.google_rating}{" "}
                <span className="text-dim">({lead.review_count})</span>
              </span>
            )}
            {lead.website ? (
              <span className="flex items-center gap-1 text-muted"><Globe className="h-3 w-3" /> site var</span>
            ) : (
              <span className="flex items-center gap-1 text-dim"><Globe className="h-3 w-3" /> site yok</span>
            )}
            {lead.phone && (
              <span className="flex items-center gap-1 text-muted"><Phone className="h-3 w-3" /> tel</span>
            )}
          </div>
        </div>

        {selected && (
          <div className="mt-3 pt-3 border-t border-stroke space-y-3">
            {!lead.lead_id && lead.segment !== "low" && (
              <div className="border border-review/40 bg-review/5 px-2.5 py-1.5 text-[11px] font-mono text-review">
                Ön analiz — hızlı aramada yalnız Maps sinyalleri kullanıldı.
                Kesin değerlendirme için <span className="font-bold">Yeni Tarama</span> çalıştır.
              </div>
            )}
            {/* Action buttons */}
            <div className="flex flex-wrap items-center gap-2">
              {lead.maps_url && (
                <a
                  href={lead.maps_url}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider px-2.5 py-1 border border-stroke-2 text-muted hover:text-bright hover:border-accent transition-all"
                >
                  <ExternalLink className="h-3 w-3" /> Maps
                </a>
              )}
              {lead.website && (
                <a
                  href={lead.website}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider px-2.5 py-1 border border-stroke-2 text-muted hover:text-bright hover:border-accent transition-all"
                >
                  <Globe className="h-3 w-3" /> Site
                </a>
              )}
              {wa && (
                <a
                  href={wa}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider px-2.5 py-1 border border-ok/50 text-ok hover:bg-ok/10 transition-all"
                >
                  <MessageSquare className="h-3 w-3" /> WhatsApp
                </a>
              )}
            </div>

            {/* Score breakdown */}
            {lead.score_breakdown?.length > 0 ? (
              <div className="space-y-0.5">
                <p className="font-mono text-[8px] text-dim uppercase tracking-[0.15em] mb-1">Neden bu skor?</p>
                {lead.score_breakdown.map((s, i) => (
                  <div key={i} className={`flex items-start gap-1.5 font-mono text-[11px] ${signalColor(s)}`}>
                    <span className="shrink-0">{signalIcon(s)}</span>
                    <span>{s.replace(/^[+-]?\d+\s*/, "").replace(/^Elendi:\s*/, "")}</span>
                    {s.match(/^([+-]\d+)/) && (
                      <span className="ml-auto shrink-0 font-bold">{s.match(/^([+-]\d+)/)?.[1]}</span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="font-mono text-[11px] text-dim">
                {lead.reason || "Detaylı analiz için kaydet ve audit başlat."}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
