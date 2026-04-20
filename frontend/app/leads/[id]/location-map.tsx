"use client";

interface Props {
  address: string | null;
  name: string;
}

export function LocationMap({ address, name }: Props) {
  if (!address) return null;

  const query = encodeURIComponent(`${name} ${address}`);
  const embedUrl = `https://maps.google.com/maps?q=${query}&output=embed&hl=tr`;
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${query}`;

  return (
    <div className="border border-stroke overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 bg-panel-high border-b border-stroke">
        <p className="font-mono text-[11px] text-dim uppercase tracking-[0.2em]">📍 Konum</p>
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="font-mono text-[11px] text-accent hover:underline tracking-wider"
        >
          Google Maps'te Aç ↗
        </a>
      </div>
      <iframe
        src={embedUrl}
        width="100%"
        height="220"
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
        className="block border-0"
        title={`${name} konumu`}
      />
    </div>
  );
}
