"use client";

import { useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { leadsApi } from "@/lib/api";
import type { Lead } from "@/types";

interface Props {
  initial: Lead[];
}

function scoreColor(score: number) {
  if (score >= 70) return "#e53935";
  if (score >= 55) return "#fb8c00";
  return "#9e9e9e";
}

export function HotLeads({ initial }: Props) {
  const [leads, setLeads] = useState<Lead[]>(initial);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  if (leads.length === 0) return null;

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.preventDefault();
    e.stopPropagation();
    setDeletingId(id);
    try {
      await leadsApi.delete(id);
      setLeads((prev) => prev.filter((l) => l.id !== id));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <p className="font-mono text-[11px] text-dim tracking-[0.25em] uppercase mb-3">
        ▸ Öne Çıkan Adaylar
      </p>
      <div className="border border-stroke bg-panel">
        <ul className="divide-y divide-stroke">
          {leads.map((lead) => {
            const score = lead.opportunity_score ?? 0;
            const color = scoreColor(score);
            return (
              <li key={lead.id} className="relative group">
                <Link
                  href={`/leads/${lead.id}`}
                  className="flex items-center justify-between px-5 py-3.5 hover:bg-panel-high transition-colors"
                >
                  {/* Score ring */}
                  <div className="flex items-center gap-4">
                    <div
                      className="relative flex h-10 w-10 items-center justify-center border shrink-0"
                      style={{ borderColor: color, boxShadow: `0 0 10px ${color}40` }}
                    >
                      <span
                        className="font-mono font-bold text-sm"
                        style={{ color }}
                      >
                        {score || "—"}
                      </span>
                      {score >= 75 && (
                        <span
                          className="absolute inset-0 border"
                          style={{
                            borderColor: color,
                            animation: "ping 2s ease-out infinite",
                            opacity: 0,
                          }}
                        />
                      )}
                    </div>

                    <div>
                      <p className="font-medium text-bright text-sm">{lead.name}</p>
                      <p className="text-[12px] font-mono text-muted mt-0.5 tracking-wider">
                        {lead.sector}
                        {lead.city ? ` · ${lead.city}` : ""}
                        {lead.google_rating ? ` · ⭐ ${lead.google_rating}` : ""}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Badge value={lead.status} />
                    <button
                      type="button"
                      onClick={(e) => handleDelete(e, lead.id)}
                      disabled={deletingId === lead.id}
                      className="font-mono text-[12px] text-dim hover:text-hot disabled:opacity-40 transition-colors p-1"
                      title="Kaldır"
                    >
                      {deletingId === lead.id ? "…" : "✕"}
                    </button>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
