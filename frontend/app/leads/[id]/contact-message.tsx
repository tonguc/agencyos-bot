"use client";

import { useState } from "react";
import type { OutreachMessage } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function MessageText({ text }: { text: string }) {
  const [notice, setNotice] = useState("");
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setNotice("Kopyalandı");
    } catch {
      setNotice("Kopyalanamadı; metni seçerek kopyalayabilirsiniz.");
    }
  }
  return <div className="space-y-3">
    <p className="text-sm text-bright leading-relaxed whitespace-pre-wrap">{text}</p>
    <div className="flex flex-wrap gap-3 text-xs">
      <button type="button" onClick={copy} className="border border-stroke-2 px-3 py-2">Kopyala</button>
      <a href={`https://wa.me/?text=${encodeURIComponent(text)}`} target="_blank" rel="noopener noreferrer" className="border border-ok/40 text-ok px-3 py-2">WhatsApp’ta aç</a>
    </div>
    <p role="status" className="text-xs text-muted">{notice}</p>
  </div>;
}

export function FirstContactMessage({ output, outreach }: {
  output?: { short_message?: string; full_message?: string } | null;
  outreach?: OutreachMessage | null;
}) {
  const alternatives = [
    { label: "Kısa doğrulama", text: outreach?.v1 },
    { label: "Doğrudan öneri", text: outreach?.v2 },
    { label: "Nazik giriş", text: outreach?.v3 },
    { label: "Ayrıntılı öneri", text: outreach?.v4 },
    { label: "Ek açıklama", text: output?.full_message },
  ];
  const primary = output?.short_message || alternatives.find(item => item.text)?.text;
  if (!primary) return null;
  const others = alternatives.filter((item, i, items) => item.text && item.text !== primary && items.findIndex(other => other.text === item.text) === i);
  return <Card>
    <CardHeader><CardTitle>İlk temas mesajı</CardTitle>
      <p className="text-xs text-muted">Önce ilgiyi ve ihtiyacı netleştirin; yanıtına göre teklifinizi hazırlayın.</p>
    </CardHeader>
    <CardContent className="space-y-4">
      <MessageText key={primary} text={primary} />
      {outreach?.sent_at && <p className="text-xs text-muted">Önceki mesaj için gönderim kaydı var. Tekrar yazmadan önce konuşmayı kontrol edin.</p>}
      {others.length > 0 && <details className="border-t border-stroke pt-3">
        <summary className="cursor-pointer text-sm text-muted">Alternatif mesajlar</summary>
        <p className="text-xs text-muted mt-3">Bunlar seçeneklerdir; art arda gönderilecek bir mesaj dizisi değildir.</p>
        {others.map(item => <div key={item.label} className="mt-4 border border-stroke p-4 space-y-2">
          <h4 className="text-sm font-medium">{item.label}</h4><MessageText text={item.text!} />
        </div>)}
      </details>}
      <p className="text-xs text-muted">WhatsApp yalnızca mesaj taslağını açar; gönderimi siz tamamlarsınız.</p>
    </CardContent>
  </Card>;
}

export function ProposalSendNote() {
  return <div className="mt-6 border-t border-stroke pt-4 space-y-3">
    <h3 className="text-sm font-semibold">PDF gönderim notu</h3>
    <p className="text-xs text-muted">Teklifi paylaşmaya hazır olduğunuzda kullanın. PDF’yi indirip WhatsApp’ta belge olarak ayrıca ekleyin.</p>
    <MessageText text="Merhaba, işletmeniz için hazırladığım çalışma önerisini ekte paylaşıyorum. Önerilen kapsamı ve nasıl ilerleyebileceğimizi özetledim. Önceliklerinize uymayan bir nokta varsa birlikte düzenleyebiliriz." />
  </div>;
}
