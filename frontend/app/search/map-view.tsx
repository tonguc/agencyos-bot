"use client";

import { useMemo } from "react";
import type { SearchResultItem } from "@/types";
import { SEGMENT_LABELS } from "./segment";

interface Props {
  results: SearchResultItem[];
  selectedIdx: number | null;
  onSelect: (idx: number) => void;
}

const SEG_STYLE: Record<string, { bg: string; ring: string; glow: string }> = {
  hot:    { bg: "#e53935", ring: "#e53935", glow: "0 0 8px #e5393599" },
  warm:   { bg: "#fb8c00", ring: "#fb8c00", glow: "0 0 8px #fb8c0099" },
  ok:     { bg: "#6b8db5", ring: "#6b8db5", glow: "0 0 8px #6b8db599" },
  low:    { bg: "#9e9e9e", ring: "#9e9e9e", glow: "none" },
  review: { bg: "#d4a017", ring: "#d4a017", glow: "0 0 8px #d4a01799" },
};

const SEG_DOT: Record<string, string> = {
  hot:    "bg-hot",
  warm:   "bg-warm",
  ok:     "bg-ok",
  low:    "bg-low",
  review: "bg-review",
};

export function MapView({ results, selectedIdx, onSelect }: Props) {
  const geo = useMemo(() => {
    const points = results
      .map((r, i) => ({ r, i }))
      .filter(({ r }) => typeof r.lat === "number" && typeof r.lng === "number");
    if (points.length === 0) return null;
    const lats = points.map((p) => p.r.lat as number);
    const lngs = points.map((p) => p.r.lng as number);
    const minLat = Math.min(...lats), maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs), maxLng = Math.max(...lngs);
    const padLat = Math.max((maxLat - minLat) * 0.15, 0.01);
    const padLng = Math.max((maxLng - minLng) * 0.15, 0.01);
    return {
      points,
      minLat: minLat - padLat, maxLat: maxLat + padLat,
      minLng: minLng - padLng, maxLng: maxLng + padLng,
    };
  }, [results]);

  if (!geo) {
    return (
      <div className="h-full min-h-[280px] flex items-center justify-center border border-dashed border-stroke">
        <p className="font-mono text-[13px] text-dim">Konum bilgisi olan sonuç yok.</p>
      </div>
    );
  }

  const bbox = `${geo.minLng},${geo.minLat},${geo.maxLng},${geo.maxLat}`;
  const osmSrc = `https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(bbox)}&layer=mapnik`;

  // Koordinatları % pozisyona çevir
  const toPos = (lat: number, lng: number) => ({
    left: `${((lng - geo.minLng) / (geo.maxLng - geo.minLng)) * 100}%`,
    top:  `${((geo.maxLat - lat) / (geo.maxLat - geo.minLat)) * 100}%`,
  });

  return (
    <div className="relative h-full min-h-[420px] overflow-hidden border border-stroke bg-panel">
      {/* Basemap */}
      <iframe
        src={osmSrc}
        className="absolute inset-0 w-full h-full border-0"
        style={{ filter: "saturate(0.7) brightness(0.85) contrast(1.1)" }}
        loading="lazy"
        title="Harita"
      />

      {/* Markers */}
      {geo.points.map(({ r, i }) => {
        const pos = toPos(r.lat as number, r.lng as number);
        const seg = SEG_STYLE[r.segment] ?? SEG_STYLE.low;
        const isSel = selectedIdx === i;

        return (
          <button
            key={i}
            type="button"
            onClick={() => onSelect(i)}
            className="absolute -translate-x-1/2 -translate-y-1/2 group"
            style={{ ...pos, zIndex: isSel ? 20 : 10 }}
            title={r.name}
          >
            {/* Pulse ring — sadece seçili */}
            {isSel && (
              <span
                className="absolute inset-0 rounded-full animate-ping"
                style={{
                  backgroundColor: seg.bg,
                  opacity: 0.35,
                  transform: "scale(2.2)",
                }}
              />
            )}
            {/* Ana marker */}
            <span
              className="relative block rounded-full border-2 border-white transition-transform"
              style={{
                width:  isSel ? 16 : 11,
                height: isSel ? 16 : 11,
                backgroundColor: seg.bg,
                boxShadow: isSel ? seg.glow : "0 1px 3px rgba(0,0,0,0.5)",
                transform: isSel ? "scale(1.15)" : "scale(1)",
              }}
            />
            {/* Tooltip */}
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 whitespace-nowrap
              hidden group-hover:block font-mono text-[11px] text-bright bg-panel border border-stroke
              px-2 py-1 pointer-events-none z-30">
              {r.name}
              {r.google_rating ? ` · ⭐${r.google_rating}` : ""}
            </span>
          </button>
        );
      })}

      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex flex-wrap gap-2
        bg-panel/90 backdrop-blur-sm border border-stroke px-2.5 py-1.5">
        {(["hot", "warm", "review", "ok", "low"] as const).map((seg) => (
          <span key={seg} className="inline-flex items-center gap-1.5 font-mono text-[11px] text-muted">
            <span className={`h-2 w-2 rounded-full shrink-0 ${SEG_DOT[seg]}`} />
            {SEGMENT_LABELS[seg]}
          </span>
        ))}
      </div>
    </div>
  );
}
