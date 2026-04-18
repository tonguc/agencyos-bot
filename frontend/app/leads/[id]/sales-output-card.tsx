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
        <p className="text-xs text-slate-400 mt-0.5">Müşteriye gönderilecek versiyon</p>
      </CardHeader>
      <CardContent className="space-y-4">

        {/* SHORT — gönderilecek */}
        <div className="rounded-xl border border-green-200 bg-green-50 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-green-700 uppercase tracking-wide">
              Satış Mesajı (Gönderilecek)
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => copy(short, "short")}
                className="text-xs font-medium text-green-700 hover:text-green-900 bg-white border border-green-200 hover:border-green-300 px-3 py-1 rounded-lg transition-colors"
              >
                {copied === "short" ? "✓ Kopyalandı" : "Kopyala"}
              </button>
              {short && (
                <a
                  href={whatsappLink(short)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-medium text-white bg-[#25D366] hover:bg-[#1ebe5c] px-3 py-1 rounded-lg transition-colors"
                >
                  WhatsApp
                </a>
              )}
            </div>
          </div>
          <p className="text-sm text-slate-800 leading-relaxed whitespace-pre-wrap">{short}</p>
          <p className="text-xs text-green-600">{short.length} karakter</p>
        </div>

        {/* FULL — isteğe bağlı */}
        <div className="rounded-xl border border-slate-200 bg-white">
          <button
            type="button"
            onClick={() => setFullOpen((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-3 text-left"
          >
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Detaylı Açıklama (İsteğe Bağlı)
            </p>
            <span className="text-xs text-slate-400">{fullOpen ? "Kapat ▲" : "Göster ▼"}</span>
          </button>

          {fullOpen && (
            <div className="px-4 pb-4 space-y-3 border-t border-slate-100 pt-3">
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => copy(full, "full")}
                  className="text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-50 border border-slate-200 hover:border-slate-300 px-3 py-1 rounded-lg transition-colors"
                >
                  {copied === "full" ? "✓ Kopyalandı" : "Kopyala"}
                </button>
                {full && (
                  <a
                    href={whatsappLink(full)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-medium text-white bg-[#25D366] hover:bg-[#1ebe5c] px-3 py-1 rounded-lg transition-colors"
                  >
                    WhatsApp
                  </a>
                )}
              </div>
              <pre className="whitespace-pre-wrap text-sm text-slate-700 leading-relaxed font-sans">
                {full}
              </pre>
            </div>
          )}
        </div>

      </CardContent>
    </Card>
  );
}
