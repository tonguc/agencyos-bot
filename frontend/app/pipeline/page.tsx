import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

const STAGES = [
  "Yeni", "Audit", "Mesaj", "Cevap", "Demo", "Teklif", "Kapandi", "Soguk",
];

async function getPipelineCounts() {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/leads/pipeline`,
      {
        headers: { "X-API-Key": process.env.NEXT_PUBLIC_API_KEY ?? "changeme" },
        cache: "no-store",
      }
    );
    if (!res.ok) return null;
    const data = await res.json();
    return data.counts as Record<string, number>;
  } catch {
    return null;
  }
}

export default async function PipelinePage() {
  const counts = await getPipelineCounts();

  return (
    <div className="flex flex-col flex-1">
      <Header
        title="Pipeline"
        description="Lead'lerin aşamalara göre dağılımı"
      />
      <div className="p-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {STAGES.map((stage) => (
            <Link key={stage} href={`/leads?status=${stage}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between">
                    <Badge value={stage} />
                  </div>
                  <p className="mt-3 text-3xl font-bold text-slate-900">
                    {counts ? (counts[stage] ?? 0) : "—"}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">lead</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {!counts && (
          <p className="mt-6 text-sm text-slate-400 text-center">
            API'ye bağlanılamadı. Backend çalışıyor mu?
          </p>
        )}
      </div>
    </div>
  );
}
