import { Header } from "@/components/layout/header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScoreBar } from "@/components/ui/score-bar";
import { formatDateTime } from "@/lib/utils";
import { LeadActions } from "./lead-actions";
import type { Audit, Lead, OutreachMessage, Proposal } from "@/types";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const KEY = process.env.NEXT_PUBLIC_API_KEY ?? "changeme";
const hdrs = { "X-API-Key": KEY };

async function get<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${API}${path}`, { headers: hdrs, cache: "no-store" });
    return r.ok ? r.json() : null;
  } catch { return null; }
}

interface Props { params: Promise<{ id: string }> }

export default async function LeadDetailPage({ params }: Props) {
  const { id } = await params;

  const [lead, audit, outreach, proposal] = await Promise.all([
    get<Lead>(`/api/leads/${id}`),
    get<Audit>(`/api/leads/${id}/audit`),
    get<OutreachMessage>(`/api/leads/${id}/outreach`),
    get<Proposal>(`/api/leads/${id}/proposal`),
  ]);

  if (!lead) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <p className="text-slate-400">Lead bulunamadı.</p>
          <Link href="/leads" className="text-sm text-blue-500 mt-2 inline-block">← Geri dön</Link>
        </div>
      </div>
    );
  }

  const result = audit?.result as Record<string, unknown> | null;
  const salesOutput = result?.sales_output as {
    headline?: string;
    demand_block?: string;
    top_3_problems?: string[];
    insight_block?: string;
    solution_block?: string[];
    cta_block?: string;
    full_text?: string;
  } | null | undefined;

  return (
    <div className="flex flex-col flex-1">
      <Header
        title={lead.name}
        description={`${lead.sector} · ${lead.city}${lead.district ? ` / ${lead.district}` : ""}`}
        actions={
          <div className="flex items-center gap-2">
            <Badge value={lead.status} />
            <Link href="/leads" className="text-xs text-slate-400 hover:text-slate-600">← Lead'ler</Link>
          </div>
        }
      />

      <div className="p-6 space-y-5 max-w-4xl">
        {/* Actions */}
        <Card>
          <CardHeader><CardTitle>İşlemler</CardTitle></CardHeader>
          <CardContent>
            <LeadActions
              leadId={id}
              hasAudit={!!audit}
              hasOutreach={!!outreach}
              hasProposal={!!proposal}
              proposalId={proposal?.id}
            />
          </CardContent>
        </Card>

        {/* Lead info */}
        <Card>
          <CardHeader><CardTitle>Bilgiler</CardTitle></CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-4 text-sm">
              {([
                ["Telefon", lead.phone],
                ["Website", lead.website ? (
                  <a href={lead.website} target="_blank" rel="noopener noreferrer"
                    className="text-blue-600 hover:underline break-all">{lead.website}</a>
                ) : null],
                ["Adres", lead.address],
                ["Google Puan", lead.google_rating ? `${lead.google_rating} ⭐ (${lead.review_count} yorum)` : null],
                ["Fırsat Skoru", lead.opportunity_score],
                ["Öncelik", lead.priority],
                ["Eklenme", formatDateTime(lead.created_at)],
                ["Güncelleme", formatDateTime(lead.updated_at)],
              ] as [string, React.ReactNode][]).map(([k, v]) => v != null && (
                <div key={k}>
                  <dt className="text-xs text-slate-500">{k}</dt>
                  <dd className="font-medium text-slate-800 mt-0.5">{v}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>

        {/* Audit */}
        {audit && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Audit</CardTitle>
                <div className="flex gap-2">
                  {audit.urgency && <Badge value={audit.urgency} />}
                  {audit.lead_quality && <Badge value={audit.lead_quality} />}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Scores */}
              <div className="grid grid-cols-2 gap-4">
                <ScoreBar label="UX" value={audit.ux_score} />
                <ScoreBar label="SEO" value={audit.seo_score} />
                <ScoreBar label="Dönüşüm" value={audit.conversion_score} />
                <ScoreBar label="Genel" value={audit.general_score} />
              </div>

              {/* Killer insight */}
              {audit.killer_insight && (
                <div className="rounded-lg bg-amber-50 border border-amber-200 p-4">
                  <p className="text-xs font-semibold text-amber-600 uppercase tracking-wide mb-1">Killer Insight</p>
                  <p className="text-sm text-amber-900 font-medium">{audit.killer_insight}</p>
                  {audit.killer_metric && (
                    <p className="text-xs text-amber-700 mt-1">Metrik: {audit.killer_metric}</p>
                  )}
                </div>
              )}

              {/* Personal insight */}
              {audit.personal_insight && (
                <div className="rounded-lg bg-slate-50 border border-slate-200 p-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Kişisel İçgörü</p>
                  <p className="text-sm text-slate-700">{audit.personal_insight}</p>
                </div>
              )}

              {/* Site data */}
              <div className="flex flex-wrap gap-3 text-xs">
                {[
                  ["Hız", audit.site_speed != null ? `${audit.site_speed}/100` : null],
                  ["SSL", audit.has_ssl ? "✓ Var" : "✗ Yok"],
                  ["Form", audit.has_form ? "✓ Var" : "✗ Yok"],
                  ["Telefon", audit.has_tel ? "✓ Var" : "✗ Yok"],
                ].map(([k, v]) => v && (
                  <span key={String(k)} className="rounded-md bg-slate-100 px-2 py-1 text-slate-600">
                    {k}: <span className="font-medium">{v}</span>
                  </span>
                ))}
              </div>

              {/* UX errors */}
              {Array.isArray(result?.ux_hatalar) && (result.ux_hatalar as unknown[]).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">UX Hatalar</p>
                  <ul className="space-y-1">
                    {(result.ux_hatalar as {sorun: string; siddet?: string}[]).map((h, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                        <span className={`mt-0.5 h-2 w-2 rounded-full shrink-0 ${h.siddet === "yuksek" ? "bg-red-500" : h.siddet === "orta" ? "bg-orange-400" : "bg-slate-300"}`} />
                        {h.sorun}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* SEO gaps */}
              {Array.isArray(result?.seo_aciklar) && (result.seo_aciklar as unknown[]).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">SEO Açıklar</p>
                  <ul className="space-y-1">
                    {(result.seo_aciklar as {sorun: string}[]).map((s, i) => (
                      <li key={i} className="text-sm text-slate-700">• {s.sorun}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Hook */}
              {audit.hook_text && (
                <div className="rounded-lg bg-blue-50 border border-blue-200 p-4">
                  <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1">
                    Hook ({audit.hook_type})
                  </p>
                  <p className="text-sm text-blue-900">{audit.hook_text}</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Satış Özeti */}
        {salesOutput && (
          <Card>
            <CardHeader>
              <CardTitle>Satış Özeti</CardTitle>
              <p className="text-xs text-slate-400 mt-0.5">Müşteriye gönderilecek versiyon</p>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Headline */}
              {salesOutput.headline && (
                <p className="font-semibold text-slate-800 text-base">{salesOutput.headline}</p>
              )}

              {/* Demand block */}
              {salesOutput.demand_block && (
                <p className="text-sm text-slate-600 leading-relaxed">{salesOutput.demand_block}</p>
              )}

              {/* Top 3 problems */}
              {salesOutput.top_3_problems && salesOutput.top_3_problems.length > 0 && (
                <div className="rounded-lg bg-red-50 border border-red-100 p-4 space-y-2">
                  <p className="text-xs font-semibold text-red-500 uppercase tracking-wide">3 Kritik Nokta</p>
                  {salesOutput.top_3_problems.map((p, i) => (
                    <p key={i} className="text-sm text-red-900">{p}</p>
                  ))}
                </div>
              )}

              {/* Insight block */}
              {salesOutput.insight_block && (
                <div className="rounded-lg bg-amber-50 border border-amber-100 p-4">
                  <p className="text-xs font-semibold text-amber-600 uppercase tracking-wide mb-1">İçgörü</p>
                  <p className="text-sm text-amber-900 leading-relaxed">{salesOutput.insight_block}</p>
                </div>
              )}

              {/* Solution block */}
              {salesOutput.solution_block && salesOutput.solution_block.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Çözüm Çerçevesi</p>
                  {salesOutput.solution_block.map((s, i) => (
                    <p key={i} className="text-sm text-slate-600">• {s}</p>
                  ))}
                </div>
              )}

              {/* CTA */}
              {salesOutput.cta_block && (
                <div className="rounded-lg bg-blue-50 border border-blue-200 p-4">
                  <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1">CTA</p>
                  <p className="text-sm text-blue-900 leading-relaxed">{salesOutput.cta_block}</p>
                </div>
              )}

              {/* Full text copy area */}
              {salesOutput.full_text && (
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Tam Metin</p>
                  <pre className="whitespace-pre-wrap text-xs text-slate-600 bg-slate-50 rounded-lg p-4 leading-relaxed border border-slate-100 font-sans">
                    {salesOutput.full_text}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Outreach */}
        {outreach && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Outreach Mesajları</CardTitle>
                {outreach.sent_version && (
                  <span className="text-xs text-slate-500">
                    {outreach.sent_version.toUpperCase()} gönderildi ({outreach.sent_channel})
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {(["v1", "v2", "v3", "v4"] as const).map((v) =>
                outreach[v] ? (
                  <div key={v} className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-600 uppercase">{v}</span>
                      {outreach.recommended === v && <Badge value="Önerilen" />}
                      {outreach.sent_version === v && <Badge value="Gönderildi" />}
                    </div>
                    <pre className="whitespace-pre-wrap text-xs text-slate-600 bg-slate-50 rounded-lg p-3 leading-relaxed border border-slate-100">
                      {outreach[v]}
                    </pre>
                  </div>
                ) : null
              )}
            </CardContent>
          </Card>
        )}

        {/* Proposal */}
        {proposal && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Teklif</CardTitle>
                <span className="text-xs text-slate-400">{formatDateTime(proposal.created_at)}</span>
              </div>
            </CardHeader>
            <CardContent>
              {proposal.pdf_path && (
                <p className="text-xs text-slate-500 font-mono bg-slate-50 p-2 rounded mb-3">{proposal.pdf_path}</p>
              )}
              {proposal.content && typeof proposal.content === "object" && (
                <dl className="space-y-3 text-sm">
                  {(["baslik", "giris", "neden_simdi", "paket_adi", "fiyat_araligi", "cta"] as string[]).map((k) => {
                    const v = (proposal.content as Record<string, unknown>)[k];
                    return v ? (
                      <div key={k}>
                        <dt className="text-xs text-slate-500 uppercase tracking-wide">{k.replace(/_/g, " ")}</dt>
                        <dd className="text-slate-700 mt-0.5">{String(v)}</dd>
                      </div>
                    ) : null;
                  })}
                </dl>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
