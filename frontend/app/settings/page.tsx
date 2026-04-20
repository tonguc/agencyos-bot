"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const KEY  = process.env.NEXT_PUBLIC_API_KEY  ?? "changeme";
const hdrs = { "X-API-Key": KEY };

interface AppSettings {
  app_env: string;
  claude_model: string;
  pagespeed_configured: boolean;
  apify_configured: boolean;
}

interface ServiceUsage {
  ok: boolean;
  label: string;
  detail: string | null;
  dashboard_url: string | null;
}

interface UsageData {
  claude: ServiceUsage;
  openai: ServiceUsage;
  apify: ServiceUsage;
}

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className="inline-block h-2 w-2 rounded-full shrink-0"
      style={{ background: ok ? "#34d399" : "#f43f5e", boxShadow: ok ? "0 0 4px #34d399" : "0 0 4px #f43f5e" }}
    />
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-stroke last:border-0">
      <span className="font-mono text-[12px] text-dim tracking-wider">{label}</span>
      <span className="font-mono text-[12px] text-muted text-right">{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="border border-stroke bg-panel">
      <div className="px-5 py-3 border-b border-stroke flex items-center">
        <p className="font-mono text-[11px] text-dim tracking-[0.25em] uppercase flex-1">{title}</p>
      </div>
      <div className="px-5">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  const [s,       setS]       = useState<AppSettings | null>(null);
  const [usage,   setUsage]   = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [sr, ur] = await Promise.all([
        fetch(`${BASE}/api/settings`,       { headers: hdrs }),
        fetch(`${BASE}/api/settings/usage`, { headers: hdrs }),
      ]);
      if (sr.ok) setS(await sr.json());
      if (ur.ok) setUsage(await ur.json());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const services: ServiceUsage[] = usage ? [usage.claude, usage.openai, usage.apify] : [];

  return (
    <div className="flex flex-col flex-1">
      <Header title="Ayarlar" description="API bağlantıları ve kullanım" />
      <div className="p-4 md:p-6 max-w-xl space-y-4">

        {loading && (
          <p className="font-mono text-[13px] text-dim text-center py-10 tracking-wider">Yükleniyor…</p>
        )}

        {!loading && s && (
          <Section title="Sistem">
            <Row label="Ortam"        value={s.app_env} />
            <Row label="Claude Model" value={<span className="text-accent">{s.claude_model}</span>} />
          </Section>
        )}

        {/* API Usage */}
        <Section title={
          <span className="flex items-center justify-between w-full">
            <span>API Kullanımı</span>
            <button
              type="button"
              onClick={load}
              disabled={loading}
              className="font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 border border-stroke text-dim hover:border-accent hover:text-accent disabled:opacity-40 transition-all"
            >
              {loading ? "…" : "↻"}
            </button>
          </span>
        }>
          {loading ? (
            <p className="font-mono text-[12px] text-dim py-4">Kontrol ediliyor…</p>
          ) : services.length === 0 ? (
            <p className="font-mono text-[12px] text-dim py-4">Yüklenemedi.</p>
          ) : (
            services.map((svc) => (
              <div key={svc.label} className="py-3 border-b border-stroke last:border-0">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <Dot ok={svc.ok} />
                    <span className="font-mono text-[13px] text-bright font-semibold">{svc.label}</span>
                  </div>
                  {svc.dashboard_url && (
                    <a
                      href={svc.dashboard_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-[10px] text-accent hover:underline tracking-wider uppercase"
                    >
                      Panele Git →
                    </a>
                  )}
                </div>
                {svc.detail && (
                  <p className="font-mono text-[11px] text-dim ml-4">{svc.detail}</p>
                )}
              </div>
            ))
          )}
        </Section>

        {!loading && s && (
          <Section title="Servisler">
            <Row
              label="PageSpeed API"
              value={
                <span className="flex items-center gap-2">
                  <Dot ok={s.pagespeed_configured} />
                  {s.pagespeed_configured ? "Bağlı" : "Yapılandırılmamış"}
                </span>
              }
            />
            <Row
              label="Apify"
              value={
                <span className="flex items-center gap-2">
                  <Dot ok={s.apify_configured} />
                  {s.apify_configured ? "Bağlı" : "Yapılandırılmamış"}
                </span>
              }
            />
          </Section>
        )}

      </div>
    </div>
  );
}
