"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface SalesOutput {
  short_message?: string;
  full_message?: string;
}

export function SalesOutputCard({ output }: { output: SalesOutput }) {
  const [copied, setCopied] = useState<"short" | "full" | null>(null);
  const [fullOpen, setFullOpen] = useState(false);

  async function copy(text: string, which: "short" | "full") {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(which);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      // clipboard not available
    }
  }

  function whatsappLink(text: string) {
    return `https://wa.me/?text=${encodeURIComponent(text)}`;
  }

  const short = output.short_message ?? "";
  const full = output.full_message ?? "";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Satış Mesajı</CardTitle>
        <p className="font-mono text-[11px] text-dim mt-0.5 tracking-wider">Müşteriye gönderilecek versiyon</p>
      </CardHeader>
      <CardContent className="space-y-4">

        {/* SHORT */}
        <div className="border border-ok/30 bg-ok/5 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="font-mono text-[11px] text-ok uppercase tracking-[0.2em]">
              Satış Mesajı · Gönderilecek
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => copy(short, "short")}
                className="font-mono text-[11px] uppercase tracking-wider px-3 py-1 border border-ok/40 text-ok hover:bg-ok/10 transition-all"
              >
                {copied === "short" ? "✓ Kopyalandı" : "Kopyala"}
              </button>
              {short && (
                <a
                  href={whatsappLink(short)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-[11px] uppercase tracking-wider px-3 py-1 border border-ok/60 text-ok bg-ok/10 hover:bg-ok/20 transition-all"
                >
                  WhatsApp
                </a>
              )}
            </div>
          </div>
          <p className="text-sm text-bright leading-relaxed whitespace-pre-wrap">{short}</p>
          <p className="font-mono text-[11px] text-ok/70">{short.length} karakter</p>
        </div>

        {/* FULL */}
        <div className="border border-stroke">
          <button
            type="button"
            onClick={() => setFullOpen((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-panel-high transition-colors"
          >
            <p className="font-mono text-[11px] text-muted uppercase tracking-[0.2em]">
              Detaylı Açıklama (İsteğe Bağlı)
            </p>
            <span className="font-mono text-[11px] text-dim">{fullOpen ? "KAPAT ▲" : "GÖSTER ▼"}</span>
          </button>

          {fullOpen && (
            <div className="px-4 pb-4 space-y-3 border-t border-stroke pt-3">
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => copy(full, "full")}
                  className="font-mono text-[11px] uppercase tracking-wider px-3 py-1 border border-stroke-2 text-muted hover:border-accent hover:text-accent transition-all"
                >
                  {copied === "full" ? "✓ Kopyalandı" : "Kopyala"}
                </button>
                {full && (
                  <a
                    href={whatsappLink(full)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-[11px] uppercase tracking-wider px-3 py-1 border border-ok/40 text-ok hover:bg-ok/10 transition-all"
                  >
                    WhatsApp
                  </a>
                )}
              </div>
              <pre className="whitespace-pre-wrap text-sm text-muted leading-relaxed font-sans">
                {full}
              </pre>
            </div>
          )}
        </div>

      </CardContent>
    </Card>
  );
}
