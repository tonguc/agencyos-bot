"use client";

import type { SearchResultItem } from "@/types";

interface Props {
  results: SearchResultItem[];
  selectedIdx: number | null;
  onSelect: (idx: number) => void;
}

export function MapView({ results, selectedIdx, onSelect }: Props) {
  const points = results.map((r, i) => ({ r, i })).filter(({ r }) =>
    typeof r.lat === "number" && Number.isFinite(r.lat) && Math.abs(r.lat) <= 85 &&
    typeof r.lng === "number" && Number.isFinite(r.lng) && Math.abs(r.lng) <= 180
  );
  const selected = selectedIdx === null ? points[0] : points.find(p => p.i === selectedIdx);
  if (!selected) return (
    <div className="h-full min-h-[280px] flex items-center justify-center border border-dashed border-stroke">
      <p className="font-mono text-[13px] text-dim">{selectedIdx === null ? "Konum bilgisi olan sonuç yok." : "Seçilen adayın geçerli koordinatı yok."}</p>
    </div>
  );
  const lat = selected.r.lat as number;
  const lng = selected.r.lng as number;
  const bbox = `${lng - 0.012},${lat - 0.012},${lng + 0.012},${lat + 0.012}`;
  const src = `https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(bbox)}&layer=mapnik&marker=${encodeURIComponent(`${lat},${lng}`)}`;
  // The map owns its marker: panning and zooming cannot detach it from the map.
  return (
    <div className="h-full min-h-[420px] flex flex-col border border-stroke bg-panel">
      <div className="p-3 space-y-2">
        <label htmlFor="map-candidate" className="block font-mono text-[12px] text-muted">Haritada gösterilen aday</label>
        <select id="map-candidate" value={selected.i} onChange={e => onSelect(Number(e.target.value))}
          className="w-full bg-panel border border-stroke p-2 text-sm text-bright">
          {points.map(({ r, i }) => <option key={i} value={i}>#{i + 1} · {r.name}</option>)}
        </select>
        <p className="text-xs text-muted">Seçilen adayın kayıtlı koordinatı gösterilir; kurum veya adres doğrulaması değildir.</p>
      </div>
      <iframe key={src} src={src} title={`${selected.r.name} konumu`} className="w-full flex-1 min-h-[320px] border-0" loading="lazy" />
    </div>
  );
}
