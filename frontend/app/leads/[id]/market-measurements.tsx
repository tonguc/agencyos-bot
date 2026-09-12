type EvidenceLink = { url: string; matched: boolean; position?: number };
type Query = { kind: string; query: string; status: string; organic_status?: string; position?: number | null; organic_results?: EvidenceLink[]; ai_status?: string; ai_cited?: boolean | null; ai_references?: EvidenceLink[]; self_ad_observed?: boolean | null; location_used?: string; provider_created_at?: string };
type Market = { status: string; checked_at: string; domain: string | null; queries: Query[] };
type Commercial = { priority: string; signals: string[]; next_questions: string[] };

const aiLabels: Record<string, string> = {
  unavailable: "AI yanıtı alınamadı", not_returned: "Bu sorguda AI Overview dönmedi",
  no_references: "AI kaynak bağlantıları alınamadı", unknown_domain: "Alan adı doğrulanmalı",
};

export function MarketMeasurements({ market, commercial }: { market: unknown; commercial: unknown }) {
  if (!market || typeof market !== "object") return null;
  const m = market as Market;
  const c = commercial as Commercial | undefined;
  return <section className="border border-stroke-2 p-4 space-y-4">
    <h3 className="font-mono text-xs text-bright uppercase tracking-wider">Google ve AI görünürlüğü</h3>
    <p className="text-xs text-muted break-all">Kayıtlı alan adı: {m.domain || "Doğrulanmadı"} · Kaynak: SerpAPI / Google · Mobil · Türkçe / Türkiye</p>
    <p className="text-xs text-muted">Kontrol başlangıcı: {m.checked_at}</p>
    {m.status === "not_configured" && <p className="text-sm text-warm">SERPAPI_API_KEY yapılandırılmamış; sıralama ve AI görünürlüğü ölçülemedi.</p>}
    {m.status === "partial" && <p className="text-sm text-warm">Bazı sorgular ölçülemedi. Eksik sonuçlar görünürlük yokluğu sayılmaz.</p>}
    {m.status === "no_query" && <p className="text-sm text-muted">Sorgu oluşturmak için işletme bilgileri yetersiz.</p>}
    {(m.queries || []).map((q, index) => <div key={index} className="border border-stroke-2 p-3 space-y-2">
      <p className="text-sm text-bright">{q.kind === "brand" ? "Marka" : "Hizmet"} sorgusu: {q.query}</p>
      <p className="text-xs text-muted">Arama konumu: {q.location_used || "Sağlayıcı konumu doğrulanamadı"}{q.provider_created_at ? ` · Kaynak zamanı: ${q.provider_created_at}` : ""}</p>
      {q.status !== "measured" ? <p className="text-sm text-warm">Sorgu sonucu alınamadı.</p> : <>
        <p className="text-sm text-muted">Google organik: {q.organic_status === "unknown_domain" ? "Site alan adı bilinmediği için eşleştirilemedi" : q.organic_status !== "measured" ? "Ölçülemedi" : q.position != null ? `${q.position}. sırada eşleşti` : `İncelenen ${q.organic_results?.length || 0} sonuçta alan adı eşleşmedi`}</p>
        <p className="text-sm text-muted">Google AI Overview: {q.ai_status === "measured" ? q.ai_cited ? "Kaynak bağlantılarında alan adı eşleşti" : "Dönen kaynak bağlantılarında alan adı eşleşmedi" : aiLabels[q.ai_status || "unavailable"]}</p>
        <p className="text-sm text-muted">Kayıtlı alan adı reklamı: {q.self_ad_observed == null ? "Eşleştirilemedi" : q.self_ad_observed ? "Gözlendi" : "Bu yanıtta gözlenmedi"}</p>
        <details><summary className="cursor-pointer text-xs text-cyan">Ölçümdeki sonuç ve kaynak bağlantıları</summary>
          <ul className="mt-2 space-y-1 text-xs break-all">{(q.organic_results || []).map((r, i) => <li key={`o${i}`}><a href={r.url} target="_blank" rel="noopener noreferrer" className="text-muted">Organik #{r.position}: {r.url}{r.matched ? " · Eşleşti" : ""}</a></li>)}{(q.ai_references || []).map((r, i) => <li key={`a${i}`}><a href={r.url} target="_blank" rel="noopener noreferrer" className="text-muted">AI kaynak: {r.url}{r.matched ? " · Eşleşti" : ""}</a></li>)}</ul>
        </details>
      </>}
    </div>)}
    <p className="text-xs text-muted">Sorgular işletme adı, sektör ve bölgeden otomatik oluşturulur; hedef hizmeti temsil ettiğini kontrol edin. Ölçüm, sağlayıcının döndürdüğü ilk organik sonuçlarla (en fazla ilk 10 sıra) ve Google AI Overview kaynaklarıyla sınırlıdır. Alan adı eşleşmesi marka anılması değildir. ChatGPT, Perplexity ve bağımsız Gemini yanıtları ölçülmedi. Sonuçlar zamana ve konuma göre değişebilir; sağlayıcı önbelleği kullanılabilir.</p>
    {c && <div className="border-t border-stroke-2 pt-4 space-y-3">
      <h3 className="font-mono text-xs text-bright uppercase tracking-wider">Ödeme ihtimali · Ticari sinyaller</h3>
      <p className="text-sm text-bright">{c.priority === "investment_and_need" ? "Dijital yatırım ve teknik ihtiyaç birlikte gözlendi; görüşme önceliği var." : c.priority === "need_to_qualify" ? "Teknik ihtiyaç gözlendi; bütçe ve satın alma niyeti doğrulanmalı." : "Görüşme önceliği için yeterli kanıt yok."}</p>
      <ul className="space-y-2 text-sm text-muted">{c.signals.map((s, i) => <li key={i}>{s}</li>)}</ul>
      <p className="text-xs text-muted">Ödeme olasılığı yüzdesi hesaplanmadı. Reklam veya yorum sayısı ödeme gücü kanıtı değildir. Bütçe, karar yetkisi ve satın alma niyeti bilinmiyor; mevcut Fırsat Skoru değiştirilmedi.</p>
      <details><summary className="cursor-pointer text-xs text-cyan">Görüşmede doğrulanacak sorular</summary><ul className="mt-2 space-y-2 text-sm text-muted">{c.next_questions.map((q, i) => <li key={i}>{q}</li>)}</ul></details>
    </div>}
  </section>;
}
