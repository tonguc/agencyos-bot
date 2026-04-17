import { Header } from "@/components/layout/header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDateTime } from "@/lib/utils";
import type { Audit, Lead, OutreachMessage } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const KEY = process.env.NEXT_PUBLIC_API_KEY ?? "changeme";
const headers = { "X-API-Key": KEY };

async function getLead(id: string): Promise<Lead | null> {
  try {
    const r = await fetch(`${API}/api/leads/${id}`, { headers, cache: "no-store" });
    return r.ok ? r.json() : null;
  } catch { return null; }
}

async function getAudit(id: string): Promise<Audit | null> {
  try {
    const r = await fetch(`${API}/api/leads/${id}/audit`, { headers, cache: "no-store" });
    return r.ok ? r.json() : null;
  } catch { return null; }
}

async function getOutreach(id: string): Promise<OutreachMessage | null> {
  try {
    const r = await fetch(`${API}/api/leads/${id}/outreach`, { headers, cache: "no-store" });
    return r.ok ? r.json() : null;
  } catch { return null; }
}

interface Props { params: Promise<{ id: string }> }

export default async function LeadDetailPage({ params }: Props) {
  const { id } = await params;
  const [lead, audit, outreach] = await Promise.all([
    getLead(id), getAudit(id), getOutreach(id),
  ]);

  if (!lead) {
    return (
      <div className="flex flex-1 items-center justify-center text-slate-400">
        Lead bulunamadı.
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1">
      <Header
        title={lead.name}
        description={`${lead.sector} · ${lead.city}${lead.district ? ` / ${lead.district}` : ""}`}
        actions={<Badge value={lead.status} />}
      />

      <div className="p-6 space-y-5">
        {/* Lead info */}
        <Card>
          <CardHeader><CardTitle>Bilgiler</CardTitle></CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
              {[
                ["Telefon", lead.phone ?? "—"],
                ["Website", lead.website ?? "—"],
                ["Adres", lead.address ?? "—"],
                ["Google Puan", lead.google_rating ? `${lead.google_rating} ⭐ (${lead.review_count} yorum)` : "—"],
                ["Öncelik", lead.priority ?? "—"],
                ["Fırsat Skoru", lead.opportunity_score ?? "—"],
                ["Eklenme", formatDateTime(lead.created_at)],
              ].map(([k, v]) => (
                <div key={String(k)}>
                  <dt className="text-xs text-slate-500">{k}</dt>
                  <dd className="font-medium text-slate-800 mt-0.5 break-all">{v}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>

        {/* Audit */}
        {audit && (
          <Card>
            <CardHeader>
              <CardTitle>Audit Sonucu</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-6 mb-4">
                {[
                  ["Genel", audit.general_score],
                  ["UX", audit.ux_score],
                  ["SEO", audit.seo_score],
                  ["Dönüşüm", audit.conversion_score],
                ].map(([label, val]) => (
                  <div key={String(label)} className="text-center">
                    <p className="text-2xl font-bold text-slate-900">{val ?? "—"}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{label}</p>
                  </div>
                ))}
              </div>
              {audit.killer_insight && (
                <p className="text-sm text-slate-700 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <span className="font-semibold">Killer Insight:</span> {audit.killer_insight}
                  {audit.killer_metric && ` (${audit.killer_metric})`}
                </p>
              )}
              <div className="flex gap-2 mt-3">
                {audit.urgency && <Badge value={audit.urgency} />}
                {audit.lead_quality && <Badge value={audit.lead_quality} />}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Outreach */}
        {outreach && (
          <Card>
            <CardHeader>
              <CardTitle>Outreach Mesajları</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {(["v1", "v2", "v3", "v4"] as const).map((v) =>
                outreach[v] ? (
                  <div key={v} className="text-sm">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-slate-700">{v.toUpperCase()}</span>
                      {outreach.recommended === v && <Badge value="Önerilen" />}
                      {outreach.sent_version === v && <Badge value="Gönderildi" />}
                    </div>
                    <pre className="whitespace-pre-wrap text-slate-600 bg-slate-50 rounded-lg p-3 text-xs leading-relaxed">
                      {outreach[v]}
                    </pre>
                  </div>
                ) : null
              )}
            </CardContent>
          </Card>
        )}

        {!audit && !outreach && (
          <p className="text-sm text-slate-400 text-center py-6">
            Henüz audit veya outreach verisi yok.
          </p>
        )}
      </div>
    </div>
  );
}
