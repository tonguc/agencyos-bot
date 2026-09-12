import type { SearchResponse, SearchResultItem } from "@/types";

export function buildQueries(city: string, regions: string, services: string): string[] {
  const split = (value: string) => [...new Set(value.split(/[,;\n]/).map(x => x.trim()).filter(Boolean))];
  const locations = split(regions);
  const terms = split(services);
  if (!city.trim() || !locations.length || !terms.length) throw new Error("Şehir, en az bir ilçe ve hizmet girin.");
  const queries = [...new Set(locations.flatMap(region => terms.map(term => `${city.trim()} ${region} ${term}`)))];
  if (queries.length > 4) throw new Error("Bir aramada en fazla 4 ilçe × hizmet birleşimi kullanabilirsiniz.");
  if (queries.some(q => q.length > 200)) throw new Error("Arama ifadeleri 200 karakteri geçemez.");
  return queries;
}

export function mergeSearchResults(batches: { query: string; data: SearchResponse }[], queries: string[]): SearchResponse {
  const rows: SearchResultItem[] = [];
  const seen = new Map<string, SearchResultItem>();
  const clean = (s: string) => s.normalize("NFKC").toLocaleLowerCase("tr-TR").replace(/\s+/g, " ").trim();
  for (const batch of batches) for (const source of batch.data.results) {
    // Shared phone numbers can belong to separate branches; require name/address.
    const identity = source.name && source.address ? `${clean(source.name)}|${clean(source.address)}` : source.maps_url || "";
    const existing = identity ? seen.get(identity) : undefined;
    if (existing) { existing.source_queries = [...new Set([...(existing.source_queries || []), batch.query])]; continue; }
    const row = { ...source, source_queries: [batch.query], search_context: batch.data.parsed };
    if (identity) seen.set(identity, row);
    rows.push(row);
  }
  rows.sort((a,b) => Number(!!a.permanently_closed) - Number(!!b.permanently_closed) || (b.score ?? -1) - (a.score ?? -1));
  const summary = { hot: 0, warm: 0, review: 0, ok: 0, low: 0, total: rows.length };
  for (const row of rows) summary[row.segment]++;
  return { ...batches[0].data, results: rows, summary, search_queries: queries,
    cache_hit: batches.every(batch => batch.data.cache_hit), error: null, filter_stats: null };
}
