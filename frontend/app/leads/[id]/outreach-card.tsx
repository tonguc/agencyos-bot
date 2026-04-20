"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { outreachApi } from "@/lib/api";
import type { OutreachMessage } from "@/types";

const VERSION_LABELS: Record<string, string> = {
  v1: "Meraklı",
  v2: "Doğrudan",
  v3: "Nazik",
  v4: "Kanıtlı",
};

function toWaNumber(phone: string): string {
  const d = phone.replace(/\D/g, "");
  if (d.startsWith("90") && d.length >= 11) return d;
  if (d.startsWith("0")) return "9" + d;
  return "90" + d;
}

function waLink(phone: string | null | undefined, text: string) {
  const base = phone ? `https://wa.me/${toWaNumber(phone)}` : "https://wa.me/";
  return `${base}?text=${encodeURIComponent(text)}`;
}

interface Props {
  leadId: string;
  outreach: OutreachMessage;
  phone: string | null | undefined;
}

export function OutreachCard({ leadId, outreach, phone }: Props) {
  const [data, setData] = useState<OutreachMessage>(outreach);
  const [copied, setCopied] = useState<string | null>(null);
  const [sending, setSending] = useState<string | null>(null);

  async function copy(text: string, v: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(v);
      setTimeout(() => setCopied(null), 2000);
    } catch {}
  }

  async function handleSend(v: "v1" | "v2" | "v3" | "v4", text: string) {
    // Open WhatsApp immediately — don't wait for API
    window.open(waLink(phone, text), "_blank", "noopener,noreferrer");

    // Mark as sent in background
    setSending(v);
    try {
      const updated = await outreachApi.markSent(leadId, data.id, v, "whatsapp");
      setData(updated);
    } catch {}
    setSending(null);
  }

  const versions = (["v1", "v2", "v3", "v4"] as const).filter((v) => data[v]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Outreach Mesajları</CardTitle>
          {data.sent_version && (
            <span className="font-mono text-[11px] text-ok tracking-wider">
              ✓ {VERSION_LABELS[data.sent_version] ?? data.sent_version} gönderildi
              {data.sent_channel ? ` · ${data.sent_channel}` : ""}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {versions.map((v) => {
          const text = data[v]!;
          const isSent = data.sent_version === v;
          const isRec  = data.recommended === v;

          return (
            <div
              key={v}
              className={`border p-4 space-y-3 transition-colors ${
                isSent
                  ? "border-ok/40 bg-ok/5"
                  : isRec
                  ? "border-accent/30 bg-accent/5"
                  : "border-stroke bg-panel-high"
              }`}
            >
              {/* Header row */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px] text-dim uppercase tracking-widest">{v}</span>
                  <span className="font-mono text-[11px] text-muted">·</span>
                  <span className={`font-mono text-[11px] uppercase tracking-wider ${
                    isSent ? "text-ok" : isRec ? "text-accent" : "text-muted"
                  }`}>
                    {VERSION_LABELS[v]}
                  </span>
                  {isRec && !isSent && <Badge value="Önerilen" />}
                  {isSent && <Badge value="Gönderildi" />}
                </div>
                <span className="font-mono text-[11px] text-dim">{text.length} kr</span>
              </div>

              {/* Message preview */}
              <pre className="whitespace-pre-wrap font-mono text-[13px] text-muted leading-relaxed">
                {text}
              </pre>

              {/* Actions */}
              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => copy(text, v)}
                  className="font-mono text-[11px] uppercase tracking-wider px-3 py-1.5 border border-stroke-2 text-muted hover:border-accent hover:text-accent transition-all"
                >
                  {copied === v ? "✓ Kopyalandı" : "Kopyala"}
                </button>

                <button
                  type="button"
                  disabled={sending === v}
                  onClick={() => handleSend(v, text)}
                  className={`flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider px-3 py-1.5 border transition-all disabled:opacity-50 ${
                    isSent
                      ? "border-ok/50 text-ok bg-ok/10 hover:bg-ok/20"
                      : "border-ok/40 text-ok hover:bg-ok/10"
                  }`}
                >
                  <svg viewBox="0 0 24 24" className="h-3 w-3 fill-current shrink-0">
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
                    <path d="M12 0C5.374 0 0 5.373 0 12c0 2.117.549 4.107 1.51 5.845L.057 23.886a.5.5 0 0 0 .609.61l6.084-1.435A11.94 11.94 0 0 0 12 24c6.626 0 12-5.374 12-12S18.626 0 12 0zm0 22c-1.885 0-3.647-.52-5.153-1.42l-.37-.22-3.83.903.946-3.77-.242-.385A9.954 9.954 0 0 1 2 12C2 6.478 6.477 2 12 2s10 4.478 10 10-4.477 10-10 10z"/>
                  </svg>
                  {isSent ? "Tekrar Gönder" : sending === v ? "Açılıyor..." : "WhatsApp ile Gönder"}
                </button>

                {!phone && (
                  <span className="font-mono text-[11px] text-warm">⚠ Telefon yok — kişisiz açılır</span>
                )}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
