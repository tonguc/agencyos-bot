import type {
  AppSettings,
  Audit,
  Job,
  JobResponse,
  Lead,
  LeadListResponse,
  OutreachMessage,
  PipelineCounts,
  Proposal,
  SearchResponse,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "changeme";

async function request<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...init.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Leads ──────────────────────────────────────────────────────────────
export const leadsApi = {
  list: (params?: {
    sector?: string;
    city?: string;
    district?: string;
    status?: string;
    priority?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.sector) q.set("sector", params.sector);
    if (params?.city) q.set("city", params.city);
    if (params?.district) q.set("district", params.district);
    if (params?.status) q.set("status", params.status);
    if (params?.priority) q.set("priority", params.priority);
    if (params?.search) q.set("search", params.search);
    if (params?.limit !== undefined) q.set("limit", String(params.limit));
    if (params?.offset !== undefined) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<LeadListResponse>(`/api/leads${qs ? `?${qs}` : ""}`);
  },

  get: (id: string) => request<Lead>(`/api/leads/${id}`),

  create: (body: Partial<Lead>) =>
    request<Lead>("/api/leads", { method: "POST", body: JSON.stringify(body) }),

  update: (id: string, body: Partial<Lead>) =>
    request<Lead>(`/api/leads/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  delete: async (id: string) => {
    const res = await fetch(`${BASE}/api/leads/${id}`, {
      method: "DELETE",
      headers: { "X-API-Key": API_KEY },
    });
    if (!res.ok && res.status !== 404) {
      throw new Error(`Delete failed: ${res.status}`);
    }
  },

  pipeline: () => request<PipelineCounts>("/api/leads/pipeline"),

  deleteBySector: async (sector: string, city?: string) => {
    const q = new URLSearchParams({ sector });
    if (city) q.set("city", city);
    const res = await fetch(`${BASE}/api/leads/bulk/sector?${q}`, {
      method: "DELETE",
      headers: { "X-API-Key": API_KEY },
    });
    if (!res.ok) throw new Error(`Bulk delete failed: ${res.status}`);
  },
};

// ── Audit ──────────────────────────────────────────────────────────────
export const auditApi = {
  trigger: (leadId: string) =>
    request<JobResponse>(`/api/leads/${leadId}/audit`, { method: "POST" }),

  get: (leadId: string) => request<Audit>(`/api/leads/${leadId}/audit`),

  refreshSalesOutput: (leadId: string) =>
    request<{ sales_output: Record<string, unknown> }>(
      `/api/leads/${leadId}/sales-output`,
      { method: "POST" }
    ),
};

// ── Outreach ───────────────────────────────────────────────────────────
export const outreachApi = {
  trigger: (leadId: string) =>
    request<JobResponse>(`/api/leads/${leadId}/outreach`, { method: "POST" }),

  get: (leadId: string) =>
    request<OutreachMessage>(`/api/leads/${leadId}/outreach`),

  markSent: (leadId: string, outreachId: string, version: string, channel: string) =>
    request<OutreachMessage>(
      `/api/leads/${leadId}/outreach/${outreachId}/send`,
      { method: "PATCH", body: JSON.stringify({ version, channel }) }
    ),

  followup: (leadId: string) =>
    request<{ text: string }>(`/api/leads/${leadId}/followup`, { method: "POST" }),
};

// ── Proposals ──────────────────────────────────────────────────────────
export const proposalApi = {
  trigger: (leadId: string) =>
    request<JobResponse>(`/api/leads/${leadId}/proposal`, { method: "POST" }),

  get: (leadId: string) => request<Proposal>(`/api/leads/${leadId}/proposal`),

  pdfUrl: (proposalId: string) => `${BASE}/api/proposals/${proposalId}/pdf`,
};

// ── Jobs ───────────────────────────────────────────────────────────────
export const jobsApi = {
  list: (status?: string) => {
    const q = status ? `?status=${status}` : "";
    return request<Job[]>(`/api/jobs${q}`);
  },

  get: (id: string) => request<Job>(`/api/jobs/${id}`),

  delete: (id: string) =>
    fetch(`${BASE}/api/jobs/${id}`, {
      method: "DELETE",
      headers: { "X-API-Key": API_KEY },
    }),

  streamUrl: (id: string) => `${BASE}/api/jobs/${id}/stream`,
};

// ── Scrape ─────────────────────────────────────────────────────────────
export const scrapeApi = {
  run: (sector: string, city: string, district: string, limit: number) =>
    request<JobResponse>("/api/scrape", {
      method: "POST",
      body: JSON.stringify({ sector, city, district, limit }),
    }),
};

// ── Search ─────────────────────────────────────────────────────────────
export const searchApi = {
  run: (query: string, limit = 25) =>
    request<SearchResponse>("/api/search", {
      method: "POST",
      body: JSON.stringify({ query, limit }),
    }),
};

// ── Settings ───────────────────────────────────────────────────────────
export const settingsApi = {
  get: () => request<AppSettings>("/api/settings"),
  testClaude: () => request<{ ok: boolean; message: string }>("/api/settings/test/claude", { method: "POST" }),
  testApify: () => request<{ ok: boolean; message: string }>("/api/settings/test/apify", { method: "POST" }),
};

// ── Voice ──────────────────────────────────────────────────────────────
export interface VoiceScrapeAction {
  type: "scrape";
  job_id: string;
  sector: string;
  city: string;
  district?: string;
  limit: number;
}

export const voiceApi = {
  transcribe: (blob: Blob, filename: string) => {
    const form = new FormData();
    form.append("audio", blob, filename);
    return fetch(`${BASE}/api/voice/transcribe`, {
      method: "POST",
      headers: { "X-API-Key": API_KEY },
      body: form,
    }).then((r) => r.json() as Promise<{ text: string; error?: string }>);
  },

  speak: async (text: string): Promise<HTMLAudioElement | null> => {
    const res = await fetch(`${BASE}/api/voice/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) return null;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    return new Audio(url);
  },

  status: () => request<{ openai: boolean; claude: boolean }>("/api/voice/status"),

  chat: (message: string, history: { role: string; content: string }[], signal?: AbortSignal) =>
    request<{ reply: string; action?: VoiceScrapeAction }>("/api/voice/chat", {
      method: "POST",
      body: JSON.stringify({ message, history }),
      signal,
    }),
};
