export interface Lead {
  id: string;
  name: string;
  sector: string;
  city: string;
  district: string | null;
  address: string | null;
  phone: string | null;
  website: string | null;
  google_rating: number | null;
  review_count: number | null;
  status: string;
  priority: string | null;
  opportunity_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PipelineCounts {
  counts: Record<string, number>;
  score_tiers: Record<string, number>;
}

export interface Audit {
  id: string;
  lead_id: string;
  general_score: number | null;
  ux_score: number | null;
  seo_score: number | null;
  conversion_score: number | null;
  urgency: string | null;
  lead_quality: string | null;
  killer_insight: string | null;
  killer_metric: string | null;
  personal_insight: string | null;
  hook_type: string | null;
  hook_text: string | null;
  site_speed: number | null;
  site_title: string | null;
  has_form: boolean | null;
  has_tel: boolean | null;
  has_ssl: boolean | null;
  result: Record<string, unknown> | null;
  created_at: string;
}

export interface OutreachMessage {
  id: string;
  lead_id: string;
  v1: string | null;
  v2: string | null;
  v3: string | null;
  v4: string | null;
  recommended: string | null;
  sent_version: string | null;
  sent_at: string | null;
  sent_channel: string | null;
  created_at: string;
}

export interface Proposal {
  id: string;
  lead_id: string;
  audit_id: string | null;
  pdf_path: string | null;
  content: Record<string, unknown> | null;
  created_at: string;
}

export interface Job {
  id: string;
  type: string;
  status: "pending" | "running" | "completed" | "failed";
  progress_pct: number;
  progress_message: string | null;
  error_message: string | null;
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface JobResponse {
  job_id: string;
  status: string;
  result: unknown;
}

export interface AppSettings {
  app_env: string;
  claude_model: string;
  pagespeed_configured: boolean;
  apify_configured: boolean;
  playbooks: string[];
}

// ── Search ─────────────────────────────────────────────────────────────
export type SearchSegment = "hot" | "warm" | "ok" | "low" | "review";

export interface SearchParsedQuery {
  raw_query: string;
  city: string | null;
  district: string | null;
  category: string;
  sector: string | null;
  sub_sector_hint: string | null;
  search_string: string;
}

export interface SearchResultItem {
  qualification_notes?: string[];
  permanently_closed?: boolean;
  source_queries?: string[];
  search_context?: SearchResponse["parsed"];
  name: string;
  address: string;
  phone: string | null;
  website: string | null;
  google_rating: number | null;
  review_count: number;
  category: string | null;
  lat: number | null;
  lng: number | null;
  maps_url: string | null;
  site_status: string | null;
  score: number | null;
  segment: SearchSegment;
  priority: string | null;
  reason: string | null;
  score_breakdown: string[];
  lead_id: string | null;
  // Advanced micro-scoring (4 kriter)
  competition_density_score: number | null;
  ppc_waste_score: number | null;
  social_mismatch_score: number | null;
  ecommerce_urgency_score: number | null;
}

export interface SearchSummary {
  hot: number;
  warm: number;
  ok: number;
  low: number;
  review: number;
  total: number;
}

export interface SearchResponse {
  search_queries?: string[];
  parsed: SearchParsedQuery;
  results: SearchResultItem[];
  summary: SearchSummary;
  filter_stats: {
    toplam: number;
    gecen: number;
    elenen: number;
    gecis_orani: number;
  } | null;
  error: string | null;
  cache_hit?: boolean;
}
