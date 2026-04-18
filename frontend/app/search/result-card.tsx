"use client";

import { ExternalLink, Globe, MapPin, MessageSquare, Phone } from "lucide-react";
import type { SearchResultItem } from "@/types";
import { SEGMENT_COLORS, SEGMENT_LABELS } from "./segment";

interface Props {
  lead: SearchResultItem;
  selected: boolean;
  onSelect: () => void;
}

function whatsappLink(phone: string | null): string | null {
  if (!phone) return null;
  const digits = phone.replace(/\D/g, "");
  if (!digits) return null;
  return `https://wa.me/${digits}`;
}

export function ResultCard({ lead, selected, onSelect }: Props) {
  const c = SEGMENT_COLORS[lead.segment];
  const wa = whatsappLink(lead.phone);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(); } }}
      className={`group relative rounded-xl border bg-white p-4 cursor-pointer transition-all ${
        selected
          ? `${c.border} ring-2 ${c.ring} shadow-md`
          : "border-slate-200 hover:border-slate-300 hover:shadow-sm"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-slate-900 truncate">{lead.name || "(isimsiz)"}</h3>
          <p className="mt-0.5 text-xs text-slate-500 truncate">
            {lead.category || "—"}
          </p>
        </div>
        <div className="flex flex-col items-end shrink-0">
          {lead.score !== null ? (
            <span className={`text-lg font-bold ${c.text}`}>{lead.score}</span>
          ) : (
            <span className="text-xs text-slate-300">—</span>
          )}
          <span className={`text-[10px] font-medium uppercase tracking-wide mt-0.5 ${c.text}`}>
            {SEGMENT_LABELS[lead.segment]}
          </span>
        </div>
      </div>

      <div className="mt-3 space-y-1.5 text-xs text-slate-600">
        {lead.address && (
          <div className="flex items-start gap-1.5">
            <MapPin className="h-3.5 w-3.5 shrink-0 mt-0.5 text-slate-400" />
            <span className="line-clamp-2">{lead.address}</span>
          </div>
        )}
        <div className="flex items-center gap-3 flex-wrap text-xs">
          {lead.google_rating != null && (
            <span className="text-slate-700">
              ⭐ {lead.google_rating} <span className="text-slate-400">({lead.review_count})</span>
            </span>
          )}
          {lead.website && (
            <span className="inline-flex items-center gap-1 text-slate-600">
              <Globe className="h-3 w-3" />
              site var
            </span>
          )}
          {!lead.website && (
            <span className="inline-flex items-center gap-1 text-slate-400">
              <Globe className="h-3 w-3" />
              site yok
            </span>
          )}
          {lead.phone && (
            <span className="inline-flex items-center gap-1 text-slate-600">
              <Phone className="h-3 w-3" />
              tel
            </span>
          )}
        </div>
      </div>

      {selected && (
        <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center gap-2">
          {lead.maps_url && (
            <a
              href={lead.maps_url}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200"
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
              className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200"
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
              className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-md bg-green-50 text-green-700 hover:bg-green-100 border border-green-200"
            >
              <MessageSquare className="h-3 w-3" /> WhatsApp
            </a>
          )}
          {lead.reason && (
            <span className="text-[11px] text-slate-400 italic">{lead.reason}</span>
          )}
        </div>
      )}
    </div>
  );
}
