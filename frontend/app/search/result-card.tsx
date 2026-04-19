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
  return digits ? `https://wa.me/${digits}` : null;
}

export function ResultCard({ lead, selected, onSelect }: Props) {
  const c = SEGMENT_COLORS[lead.segment];
  const wa = whatsappLink(lead.phone);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(); }
      }}
      className={`group relative border bg-panel cursor-pointer transition-all ${
        selected ? "border-stroke-2 bg-panel-high" : "border-stroke hover:border-stroke-2"
      }`}
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
            <p className="mt-0.5 text-[10px] font-mono text-muted truncate tracking-wider">
              {lead.category || "—"}
            </p>
          </div>
          <div className="flex flex-col items-end shrink-0">
            {lead.score !== null ? (
              <span
                className="text-xl font-mono font-bold"
                style={{ color: c.color }}
              >
                {lead.score}
              </span>
            ) : (
              <span className="text-xs text-dim">—</span>
            )}
            <span
              className="text-[9px] font-mono font-medium uppercase tracking-[0.2em] mt-0.5"
              style={{ color: c.color }}
            >
              {SEGMENT_LABELS[lead.segment]}
            </span>
          </div>
        </div>

        <div className="mt-3 space-y-1 text-[11px] font-mono text-muted">
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
              <span className="flex items-center gap-1 text-muted">
                <Globe className="h-3 w-3" /> site var
              </span>
            ) : (
              <span className="flex items-center gap-1 text-dim">
                <Globe className="h-3 w-3" /> site yok
              </span>
            )}
            {lead.phone && (
              <span className="flex items-center gap-1 text-muted">
                <Phone className="h-3 w-3" /> tel
              </span>
            )}
          </div>
        </div>

        {selected && (
          <div className="mt-3 pt-3 border-t border-stroke flex flex-wrap items-center gap-2">
            {lead.maps_url && (
              <a
                href={lead.maps_url}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center gap-1 text-[9px] font-mono uppercase tracking-wider px-2.5 py-1 border border-stroke-2 text-muted hover:text-bright hover:border-accent transition-all"
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
                className="inline-flex items-center gap-1 text-[9px] font-mono uppercase tracking-wider px-2.5 py-1 border border-stroke-2 text-muted hover:text-bright hover:border-accent transition-all"
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
                className="inline-flex items-center gap-1 text-[9px] font-mono uppercase tracking-wider px-2.5 py-1 border border-ok/50 text-ok hover:bg-ok/10 transition-all"
              >
                <MessageSquare className="h-3 w-3" /> WhatsApp
              </a>
            )}
            {lead.reason && (
              <span className="text-[10px] font-mono text-dim">{lead.reason}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
