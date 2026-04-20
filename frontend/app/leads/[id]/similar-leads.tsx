import Link from "next/link";
import { formatDate } from "@/lib/utils";
import type { Lead } from "@/types";

function scoreStyle(v: number) {
  if (v >= 70) return "text-hot";
  if (v >= 40) return "text-warm";
  return "text-dim";
}

interface Props {
  leads: Lead[];
  currentId: string;
}

export function SimilarLeads({ leads, currentId }: Props) {
  const others = leads.filter((l) => l.id !== currentId).slice(0, 8);
  if (others.length === 0) return null;

  return (
    <div className="border border-stroke bg-panel overflow-hidden">
      <div className="px-5 py-3 bg-panel-high border-b border-stroke">
        <p className="font-mono text-[11px] text-dim uppercase tracking-[0.25em]">
          ▸ Aynı Taramadan Diğer Adaylar
        </p>
      </div>
      <div className="divide-y divide-stroke">
        {others.map((lead) => (
          <Link
            key={lead.id}
            href={`/leads/${lead.id}`}
            className="flex items-center justify-between px-5 py-3 hover:bg-panel-high transition-colors group"
          >
            <div className="min-w-0">
              <p className="font-medium text-bright text-sm group-hover:text-accent transition-colors truncate">
                {lead.name}
              </p>
              <p className="font-mono text-[12px] text-dim mt-0.5">
                {lead.city}{lead.district ? ` / ${lead.district}` : ""} · {formatDate(lead.created_at)}
              </p>
            </div>
            <div className="flex items-center gap-3 shrink-0 ml-4">
              {lead.google_rating && (
                <span className="font-mono text-[12px] text-dim">
                  ⭐ {lead.google_rating}
                </span>
              )}
              {lead.opportunity_score != null ? (
                <span className={`font-mono font-bold text-sm ${scoreStyle(lead.opportunity_score)}`}>
                  {lead.opportunity_score}
                </span>
              ) : (
                <span className="font-mono text-[12px] text-dim">—</span>
              )}
              <span className="font-mono text-[11px] text-dim group-hover:text-accent transition-colors">→</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
