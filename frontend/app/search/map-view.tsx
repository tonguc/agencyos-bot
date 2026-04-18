"use client";

import { useMemo } from "react";
import type { SearchResultItem } from "@/types";
import { SEGMENT_COLORS, SEGMENT_LABELS } from "./segment";

interface Props {
  results: SearchResultItem[];
  selectedIdx: number | null;
  onSelect: (idx: number) => void;
}

const PIN_COLORS: Record<string, string> = {
  hot:    "#ef4444",
  warm:   "#f59e0b",
  ok:     "#3b82f6",
  low:    "#94a3b8",
  review: "#a855f7",
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
    const padLat = Math.max((maxLat - minLat) * 0.15, 0.005);
    const padLng = Math.max((maxLng - minLng) * 0.15, 0.005);
    return {
      points,
      minLat: minLat - padLat, maxLat: maxLat + padLat,
      minLng: minLng - padLng, maxLng: maxLng + padLng,
    };
  }, [results]);

  if (!geo) {
    return (
      <div className="h-full min-h-[280px] flex items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50">
        <p className="text-sm text-slate-400">Konum bilgisi olan sonuç yok.</p>
      </div>
    );
  }

  const W = 100, H = 100;
  const project = (lat: number, lng: number): [number, number] => {
    const x = ((lng - geo.minLng) / (geo.maxLng - geo.minLng)) * W;
    // SVG y is inverted from latitude
    const y = ((geo.maxLat - lat) / (geo.maxLat - geo.minLat)) * H;
    return [x, y];
  };

  // OpenStreetMap iframe centered on bounding box (read-only, gives a real basemap).
  const bbox = `${geo.minLng},${geo.minLat},${geo.maxLng},${geo.maxLat}`;
  const osmSrc = `https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(bbox)}&layer=mapnik`;

  return (
    <div className="relative h-full min-h-[420px] rounded-xl overflow-hidden border border-slate-200 bg-white">
      <iframe
        src={osmSrc}
        className="absolute inset-0 w-full h-full"
        style={{ filter: "saturate(0.85) brightness(1.02)" }}
        loading="lazy"
        title="Harita"
      />
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="absolute inset-0 w-full h-full pointer-events-none"
        preserveAspectRatio="none"
      >
        {geo.points.map(({ r, i }) => {
          const [x, y] = project(r.lat as number, r.lng as number);
          const fill = PIN_COLORS[r.segment] || PIN_COLORS.low;
          const isSel = selectedIdx === i;
          return (
            <g
              key={i}
              transform={`translate(${x} ${y})`}
              onClick={() => onSelect(i)}
              className="cursor-pointer pointer-events-auto"
            >
              <circle
                r={isSel ? 1.8 : 1.2}
                fill={fill}
                stroke="white"
                strokeWidth={0.4}
                opacity={isSel ? 1 : 0.9}
              />
              {isSel && (
                <circle r={2.8} fill="none" stroke={fill} strokeWidth={0.4} opacity={0.6}>
                  <animate attributeName="r" from="1.8" to="3.5" dur="1.2s" repeatCount="indefinite" />
                  <animate attributeName="opacity" from="0.6" to="0" dur="1.2s" repeatCount="indefinite" />
                </circle>
              )}
            </g>
          );
        })}
      </svg>

      <div className="absolute bottom-3 left-3 flex flex-wrap gap-2 bg-white/90 backdrop-blur px-2.5 py-1.5 rounded-lg border border-slate-200 shadow-sm">
        {(["hot", "warm", "review", "ok", "low"] as const).map((seg) => (
          <span key={seg} className="inline-flex items-center gap-1 text-[10px] text-slate-600">
            <span className={`h-2 w-2 rounded-full ${SEGMENT_COLORS[seg].dot}`} />
            {SEGMENT_LABELS[seg]}
          </span>
        ))}
      </div>
    </div>
  );
}
