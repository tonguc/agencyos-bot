import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AppSettings } from "@/types";

async function getSettings(): Promise<AppSettings | null> {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/settings`,
      {
        headers: { "X-API-Key": process.env.NEXT_PUBLIC_API_KEY ?? "changeme" },
        cache: "no-store",
      }
    );
    return res.ok ? res.json() : null;
  } catch { return null; }
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-green-500" : "bg-red-400"}`} />
  );
}

export default async function SettingsPage() {
  const s = await getSettings();

  return (
    <div className="flex flex-col flex-1">
      <Header title="Ayarlar" description="API bağlantıları ve konfigürasyon" />
      <div className="p-6 max-w-2xl space-y-5">
        {!s && (
          <p className="text-sm text-slate-400 text-center py-10">API'ye bağlanılamadı.</p>
        )}

        {s && (
          <>
            <Card>
              <CardHeader><CardTitle>Sistem</CardTitle></CardHeader>
              <CardContent>
                <dl className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Ortam</dt>
                    <dd className="font-medium">{s.app_env}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Claude Model</dt>
                    <dd className="font-medium font-mono text-xs">{s.claude_model}</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Servisler</CardTitle></CardHeader>
              <CardContent>
                <dl className="space-y-3 text-sm">
                  <div className="flex items-center justify-between">
                    <dt className="text-slate-500">PageSpeed API</dt>
                    <dd className="flex items-center gap-2">
                      <StatusDot ok={s.pagespeed_configured} />
                      <span>{s.pagespeed_configured ? "Bağlı" : "Yapılandırılmamış"}</span>
                    </dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="text-slate-500">Apify</dt>
                    <dd className="flex items-center gap-2">
                      <StatusDot ok={s.apify_configured} />
                      <span>{s.apify_configured ? "Bağlı" : "Yapılandırılmamış"}</span>
                    </dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

          </>
        )}
      </div>
    </div>
  );
}
