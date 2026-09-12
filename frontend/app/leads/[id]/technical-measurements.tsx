export function TechnicalMeasurements({ data }: { data: unknown }) {
  if (!data || typeof data !== "object") return null;
  const site = data as Record<string, unknown>;
  if (!site.technical || typeof site.technical !== "object") return null;
  const t = site.technical as Record<string, unknown>;
  const lab = (t.lab || {}) as Record<string, unknown>;
  const flag = (key: string) => t.html_status !== "measured" ? "Ölçülemedi" : t[key] === true ? "Gözlendi" : "İncelenen HTML’de bulunamadı";
  const metric = (key: string, unit: string) => typeof lab[key] === "number" ? `${lab[key]}${unit}` : "Ölçülemedi";
  const rows = [
    ["HTTP yanıtı", typeof t.http_status === "number" ? String(t.http_status) : "Alınamadı"],
    ["Mobil PageSpeed", t.speed_status === "not_configured" ? "PAGESPEED_API_KEY yapılandırılmamış" : metric("performance", "/100")],
    ["LCP · ana içeriğin görünmesi", metric("lcp_ms", " ms")],
    ["CLS · görsel kayma", metric("cls", "")],
    ["TBT · toplam engelleme süresi", metric("tbt_ms", " ms")],
    ["Robots / Googlebot meta noindex", flag("meta_noindex")],
    ["HTTP robots yönergesi", flag("http_robots_present")],
    ["Canonical etiketi", flag("canonical_present")],
    ["Mobil viewport etiketi", flag("viewport_present")],
    ["JSON-LD etiketi", flag("json_ld_present")],
  ];
  return (
    <section className="border border-stroke-2 p-4 space-y-3">
      <h3 className="font-mono text-xs text-bright uppercase tracking-wider">Teknik ölçümler</h3>
      <p className="text-xs text-muted break-all">Kaynak: {typeof t.final_url === "string" ? t.final_url : "Site yanıtı alınamadı"}</p>
      {typeof t.checked_at === "string" && <p className="text-xs text-muted">Ölçüm başlangıcı: {t.checked_at}</p>}
      <dl className="grid gap-2 text-sm">
        {rows.map(([label, value]) => <div key={label} className="flex flex-wrap justify-between gap-2"><dt className="text-muted">{label}</dt><dd className="text-bright">{value}</dd></div>)}
      </dl>
      <p className="text-xs text-muted leading-relaxed">Hız verileri mobil laboratuvar testidir; gerçek kullanıcı ölçümü değildir. Etiket kontrolleri ilk HTML yanıtıyla sınırlıdır; JavaScript çalıştırılmadı. Etiket varlığı doğruluk veya geçerlilik kanıtı değildir. HTTP robots yönergesinin hangi arama robotuna yönelik olduğu ayrıca incelenmelidir.</p>
      {t.html_truncated === true && <p className="text-xs text-warm">Büyük sayfanın ilk 150.000 karakteri incelendi; eksik görünen alanlar ayrıca doğrulanmalı.</p>}
      <p className="text-xs text-muted">Bu teknik kontroller tek başına Google sıralamasını veya yapay zekâ yanıtlarında görünürlüğü göstermez; bunlar ayrı sorgularla incelenir.</p>
    </section>
  );
}
