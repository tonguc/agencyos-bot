import { Header } from "@/components/layout/header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScoreBar } from "@/components/ui/score-bar";
import { formatDateTime } from "@/lib/utils";
import { LeadActions } from "./lead-actions";
import { FirstContactMessage, ProposalSendNote } from "./contact-message";
import { LocationMap } from "./location-map";
import { SimilarLeads } from "./similar-leads";
import type { Audit, Lead, OutreachMessage, Proposal } from "@/types";
import Link from "next/link";

const proposalLabels: Record<string, string> = {
  teklif_durumu: "Belgenin niteliği", baslik: "", giris: "",
  durum_ozeti: "Başlangıç noktamız", cozum: "Size önerdiğimiz çalışma",
  baslangic_odaklari: "Çalışma kapsamı", beklenen_sonuclar: "Hedeflediğimiz katkı",
  neden_simdi: "Neden bu çalışma?", paket_adi: "Hizmet paketi", fiyat_araligi: "Ücret ve ödeme",
  teslim_suresi: "Çalışma takvimi", bakim_destek: "Yayın sonrası destek",
  kapsam_siniri: "Çalışma koşulları", bir_sonraki_adim: "Nasıl başlayalım?", cta: "",
};

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

  // Similar leads — same sector + city, sorted by score
  const similarLeads = lead
    ? await get<{ items: Lead[] }>(
        `/api/leads?sector=${encodeURIComponent(lead.sector ?? "")}&city=${encodeURIComponent(lead.city ?? "")}&limit=10`
      ).then((r) => r?.items ?? [])
    : [];

  if (!lead) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <p className="font-mono text-[13px] text-muted">Lead bulunamadı.</p>
          <Link href="/leads" className="font-mono text-[12px] text-accent mt-2 inline-block hover:underline">
            ← Geri dön
          </Link>
        </div>
      </div>
    );
  }

  const result = audit?.result as Record<string, unknown> | null;
  const salesOutput = result?.sales_output as {
    short_message?: string;
    full_message?: string;
  } | null | undefined;

  return (
    <div className="flex flex-col flex-1">
      <Header
        title={lead.name}
        description={`${lead.sector} · ${lead.city}${lead.district ? ` / ${lead.district}` : ""}`}
        actions={
          <div className="flex items-center gap-3">
            <Badge value={lead.status} />
            <Link
              href="/leads"
              className="font-mono text-[11px] text-dim hover:text-accent tracking-wider transition-colors"
            >
              ← Lead&apos;ler
            </Link>
          </div>
        }
      />

      <div className="p-6 space-y-5">

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

        {/* Lead info + map side by side */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Bilgiler</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {/* Website — full width, single line */}
            {lead.website && (
              <div>
                <dt className="font-mono text-[11px] text-dim uppercase tracking-[0.2em] mb-1">Website</dt>
                <a href={lead.website} target="_blank" rel="noopener noreferrer"
                  className="text-accent hover:underline font-mono text-[13px] truncate block max-w-full">
                  {lead.website}
                </a>
              </div>
            )}
            <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
              {lead.phone && (
                <div>
                  <dt className="font-mono text-[11px] text-dim uppercase tracking-[0.2em]">Telefon</dt>
                  <dd className="font-medium text-bright text-sm mt-1">{lead.phone}</dd>
                </div>
              )}
              {lead.address && (
                <div className="col-span-2">
                  <dt className="font-mono text-[11px] text-dim uppercase tracking-[0.2em]">Adres</dt>
                  <dd className="font-medium text-bright text-sm mt-1">{lead.address}</dd>
                </div>
              )}
              {lead.google_rating != null && (
                <div>
                  <dt className="font-mono text-[11px] text-dim uppercase tracking-[0.2em]">Google Puan</dt>
                  <dd className="font-medium text-bright text-sm mt-1">
                    {lead.google_rating} ⭐ ({lead.review_count} yorum)
                  </dd>
                </div>
              )}
              {lead.opportunity_score != null && (
                <div>
                  <dt className="font-mono text-[11px] text-dim uppercase tracking-[0.2em]">Fırsat Skoru</dt>
                  <dd className={`font-mono font-bold text-lg mt-1 ${
                    lead.opportunity_score >= 70 ? "text-hot" :
                    lead.opportunity_score >= 55 ? "text-warm" : "text-dim"
                  }`}>{lead.opportunity_score}</dd>
                </div>
              )}
              {lead.priority && (
                <div>
                  <dt className="font-mono text-[11px] text-dim uppercase tracking-[0.2em]">Öncelik</dt>
                  <dd className={`font-mono font-semibold text-sm mt-1 uppercase tracking-wider ${
                    lead.priority === "yuksek" ? "text-hot" :
                    lead.priority === "orta"   ? "text-warm" : "text-dim"
                  }`}>
                    {lead.priority === "yuksek" ? "Yüksek" :
                     lead.priority === "orta"   ? "Orta"   : "Düşük"}
                  </dd>
                </div>
              )}
              <div>
                <dt className="font-mono text-[11px] text-dim uppercase tracking-[0.2em]">Eklenme</dt>
                <dd className="font-medium text-bright text-sm mt-1">{formatDateTime(lead.created_at)}</dd>
              </div>
              <div>
                <dt className="font-mono text-[11px] text-dim uppercase tracking-[0.2em]">Güncelleme</dt>
                <dd className="font-medium text-bright text-sm mt-1">{formatDateTime(lead.updated_at)}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        {/* Map */}
        <div className="lg:col-span-3">
          <LocationMap address={lead.address} name={lead.name} />
        </div>
        </div>

        {/* Audit */}
        {audit && (
          <Card>
            <CardHeader>
              <CardTitle>Audit</CardTitle>
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
                <div className="border border-warm/30 bg-warm/5 p-4">
                  <p className="font-mono text-[11px] text-warm uppercase tracking-[0.2em] mb-2">
                    ⚡ Killer Insight
                  </p>
                  <p className="text-sm text-bright font-medium leading-relaxed">
                    {audit.killer_insight}
                  </p>
                  {audit.killer_metric && (
                    <p className="font-mono text-[12px] text-muted mt-2">Metrik: {audit.killer_metric}</p>
                  )}
                </div>
              )}

              {/* Personal insight */}
              {audit.personal_insight && (
                <div className="border border-stroke-2 bg-panel-high p-4">
                  <p className="font-mono text-[11px] text-muted uppercase tracking-[0.2em] mb-2">
                    Kişisel İçgörü
                  </p>
                  <p className="text-sm text-muted leading-relaxed">{audit.personal_insight}</p>
                </div>
              )}

              {/* Site data */}
              <div className="flex flex-wrap gap-2">
                {[
                  ["Hız", !lead.website ? "Uygulanamaz" : audit.site_speed != null ? `${audit.site_speed}/100` : "Ölçülmedi"],
                  ["SSL", !lead.website ? "Uygulanamaz" : audit.has_ssl == null ? "Bilinmiyor" : audit.has_ssl ? "✓ Var" : "✗ Yok"],
                  ["Form", !lead.website ? "Uygulanamaz" : audit.has_form == null ? "Bilinmiyor" : audit.has_form ? "✓ Var" : "✗ Yok"],
                  ["Sitede telefon bağlantısı", !lead.website ? "Uygulanamaz" : audit.has_tel == null ? "Bilinmiyor" : audit.has_tel ? "✓ Var" : "✗ Yok"],
                ].map(([k, v]) => v && (
                  <span
                    key={String(k)}
                    className="font-mono text-[11px] border border-stroke-2 px-2 py-1 text-muted uppercase tracking-wider"
                  >
                    {k}: <span className="text-bright">{v}</span>
                  </span>
                ))}
              </div>

              {/* UX errors */}
              {Array.isArray(result?.ux_hatalar) && (result.ux_hatalar as unknown[]).length > 0 && (
                <div>
                  <p className="font-mono text-[11px] text-dim uppercase tracking-[0.2em] mb-3">UX Hatalar</p>
                  <ul className="space-y-2">
                    {(result.ux_hatalar as {sorun: string; siddet?: string}[]).map((h, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-muted">
                        <span className={`mt-1 h-1.5 w-1.5 rounded-full shrink-0 ${
                          h.siddet === "yuksek" ? "bg-hot" : h.siddet === "orta" ? "bg-warm" : "bg-dim"
                        }`} />
                        {h.sorun}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* SEO gaps */}
              {Array.isArray(result?.seo_aciklar) && (result.seo_aciklar as unknown[]).length > 0 && (
                <div>
                  <p className="font-mono text-[11px] text-dim uppercase tracking-[0.2em] mb-3">SEO Açıklar</p>
                  <ul className="space-y-1">
                    {(result.seo_aciklar as {sorun: string}[]).map((s, i) => (
                      <li key={i} className="font-mono text-[13px] text-muted">· {s.sorun}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Hook */}
              {audit.hook_text && (
                <div className="border border-accent/30 bg-accent/5 p-4">
                  <p className="font-mono text-[11px] text-accent uppercase tracking-[0.2em] mb-2">
                    Hook · {audit.hook_type}
                  </p>
                  <p className="text-sm text-bright leading-relaxed">{audit.hook_text}</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <FirstContactMessage output={salesOutput} outreach={outreach} />

        {/* Proposal */}
        {proposal && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Teklif</CardTitle>
                <span className="font-mono text-[11px] text-dim">{formatDateTime(proposal.created_at)}</span>
              </div>
            </CardHeader>
            <CardContent>
              {proposal.content && typeof proposal.content === "object" && (
                <dl className="space-y-3">
                  {(["teklif_durumu", "baslik", "giris", "durum_ozeti", "cozum", "baslangic_odaklari", "beklenen_sonuclar", "neden_simdi", "paket_adi", "fiyat_araligi", "teslim_suresi", "bakim_destek", "kapsam_siniri", "bir_sonraki_adim", "cta"] as string[]).map((k) => {
                    const v = (proposal.content as Record<string, unknown>)[k];
                    return v ? (
                      <div key={k}>
                        <dt className="font-mono text-[11px] text-dim uppercase tracking-[0.2em]">
                          {proposalLabels[k] ?? k}
                        </dt>
                        <dd className={k === "baslik" ? "text-lg font-semibold text-bright mt-1" : "text-sm text-muted mt-1 leading-relaxed"}>{Array.isArray(v) ? <ul className="list-disc pl-4 space-y-1">{v.map((item, i) => <li key={i}>{String(item)}</li>)}</ul> : String(v)}</dd>
                      </div>
                    ) : null;
                  })}
                </dl>
              )}
              <ProposalSendNote />
            </CardContent>
          </Card>
        )}

        {/* Similar leads */}
        <SimilarLeads leads={similarLeads} currentId={id} />

      </div>
    </div>
  );
}
