"use client";

import { useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { leadsApi } from "@/lib/api";
import type { Lead } from "@/types";

interface Props {
  initial: Lead[];
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
    <Card>
      <CardHeader>
        <CardTitle>Öne Çıkan Lead&apos;ler</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ul className="divide-y divide-slate-100">
          {leads.map((lead) => (
            <li key={lead.id} className="relative group">
              <Link
                href={`/leads/${lead.id}`}
                className="flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition-colors"
              >
                <div>
                  <p className="font-medium text-slate-800 text-sm">{lead.name}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {lead.sector} · {lead.city}
                    {lead.google_rating ? ` · ⭐ ${lead.google_rating}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-xs text-slate-500">Fırsat</p>
                    <p className="font-bold text-slate-800 text-sm">
                      {lead.opportunity_score ?? "—"}
                    </p>
                  </div>
                  <Badge value={lead.status} />
                  <button
                    type="button"
                    onClick={(e) => handleDelete(e, lead.id)}
                    disabled={deletingId === lead.id}
                    className="text-slate-300 hover:text-red-400 disabled:opacity-40 transition-colors p-1 rounded ml-1"
                    title="Kaldır"
                  >
                    {deletingId === lead.id ? "…" : "✕"}
                  </button>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
