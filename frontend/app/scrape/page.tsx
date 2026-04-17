"use client";

import { useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { scrapeApi } from "@/lib/api";

export default function ScrapePage() {
  const [sector, setSector] = useState("klinik");
  const [city, setCity] = useState("İstanbul");
  const [district, setDistrict] = useState("");
  const [limit, setLimit] = useState(20);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ job_id: string; message?: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await scrapeApi.run(sector, city, district, limit);
      setResult({ job_id: res.job_id });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Hata oluştu");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col flex-1">
      <Header title="Lead Topla" description="Google Maps'ten yeni lead'ler topla" />
      <div className="p-6 max-w-lg">
        <Card>
          <CardHeader><CardTitle>Yeni Tarama</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Sektör</label>
                <Input value={sector} onChange={(e) => setSector(e.target.value)} placeholder="klinik" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Şehir</label>
                <Input value={city} onChange={(e) => setCity(e.target.value)} placeholder="İstanbul" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">İlçe (opsiyonel)</label>
                <Input value={district} onChange={(e) => setDistrict(e.target.value)} placeholder="Kadıköy" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Limit</label>
                <Input
                  type="number"
                  min={1}
                  max={100}
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value))}
                />
              </div>
              <Button type="submit" loading={loading} className="w-full">
                Taramayı Başlat
              </Button>
            </form>

            {result && (
              <div className="mt-4 rounded-lg bg-green-50 border border-green-200 p-3 text-sm text-green-700">
                İş kuyruğa alındı. Job ID: <span className="font-mono">{result.job_id.slice(0, 8)}</span>
              </div>
            )}
            {error && (
              <div className="mt-4 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
                {error}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
