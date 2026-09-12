"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { auditApi, outreachApi, proposalApi, jobsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import type { Job } from "@/types";

interface Props {
  leadId: string;
  hasAudit: boolean;
  hasOutreach: boolean;
  hasProposal: boolean;
  proposalId?: string;
  hasSalesOutput?: boolean;
}

interface RunningJob {
  id: string;
  label: string;
}

export function LeadActions({ leadId, hasAudit, hasOutreach, hasProposal, proposalId, hasSalesOutput }: Props) {
  const router = useRouter();
  const [runningJob, setRunningJob] = useState<RunningJob | null>(null);
  const [jobData, setJobData] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [salesLoading, setSalesLoading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  function startPolling(jobId: string) {
    if (pollRef.current) clearInterval(pollRef.current);
    let failures = 0;
    let fetching = false;
    pollRef.current = setInterval(async () => {
      if (fetching) return;
      fetching = true;
      try {
        const job = await jobsApi.get(jobId);
        failures = 0;
        setError(null);
        setJobData(job);
        if (Date.now() - Date.parse(job.created_at) > 600_000 && !["completed", "failed"].includes(job.status)) {
          setError("İş beklenenden uzun sürüyor. İşler sayfasından ve worker servisinden durumunu kontrol edin.");
        }
        if (job.status === "completed" || job.status === "failed") {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          setRunningJob(null);
          if (job.status === "completed") {
            router.refresh();
          } else {
            setError(job.error_message ?? "İş başarısız oldu");
          }
        }
      } catch {
        failures += 1;
        if (failures >= 3) {
          setError("İş durumu alınamıyor. Bağlantı yeniden deneniyor; iş arka planda devam ediyor olabilir.");
        }
      } finally {
        fetching = false;
      }
    }, 1500);
  }

  async function trigger(
    label: string,
    fn: () => Promise<{ job_id: string; status: string }>
  ) {
    setError(null);
    setJobData(null);
    setRunningJob({ id: "", label });
    try {
      const res = await fn();
      setRunningJob({ id: res.job_id, label });
      startPolling(res.job_id);
    } catch (e) {
      setRunningJob(null);
      setError(e instanceof Error ? e.message : "Hata oluştu");
    }
  }

  async function handleRefreshSales() {
    setError(null);
    setSalesLoading(true);
    try {
      await auditApi.refreshSalesOutput(leadId);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Satış mesajı yenilenemedi");
    } finally {
      setSalesLoading(false);
    }
  }

  const downloadPdf = useCallback(async () => {
    if (!proposalId) return;
    setPdfLoading(true);
    try {
      const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const key  = process.env.NEXT_PUBLIC_API_KEY  ?? "changeme";
      const res  = await fetch(`${base}/api/proposals/${proposalId}/pdf`, {
        headers: { "X-API-Key": key },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `teklif-${proposalId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF indirilemedi");
    } finally {
      setPdfLoading(false);
    }
  }, [proposalId]);

  const busy = runningJob !== null;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={hasAudit ? "outline" : "default"}
          disabled={busy}
          onClick={() => trigger("Audit", () => auditApi.trigger(leadId))}
        >
          {hasAudit ? "Audit'i Yenile" : "Audit Başlat"}
        </Button>
        <Button
          size="sm"
          variant={hasOutreach ? "outline" : "default"}
          disabled={busy || !hasAudit}
          onClick={() => trigger("Outreach", () => outreachApi.trigger(leadId))}
          title={!hasAudit ? "Önce audit gerekli" : undefined}
        >
          {hasOutreach ? "Mesajı Yenile" : "Mesaj Yaz"}
        </Button>
        <Button
          size="sm"
          variant={hasProposal ? "outline" : "default"}
          disabled={busy || !hasAudit}
          onClick={() => trigger("Teklif", () => proposalApi.trigger(leadId))}
          title={!hasAudit ? "Önce audit gerekli" : undefined}
        >
          {hasProposal ? "Teklifi Yenile" : "Teklif Oluştur"}
        </Button>
        {proposalId && (
          <Button
            size="sm"
            variant="outline"
            disabled={pdfLoading}
            onClick={downloadPdf}
          >
            {pdfLoading ? "İndiriliyor…" : "PDF İndir ↓"}
          </Button>
        )}
        {hasAudit && (
          <Button
            size="sm"
            variant="outline"
            disabled={busy || salesLoading}
            onClick={handleRefreshSales}
            title="Satış mesajını yeni promptla yeniden yaz (audit tekrar çalışmaz)"
          >
            {salesLoading ? "Yenileniyor…" : "Satış Mesajını Yenile"}
          </Button>
        )}
      </div>

      {/* Job progress */}
      {runningJob && (
        <div className="border border-accent/30 bg-accent/5 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[12px] text-accent tracking-wider uppercase">
              {runningJob.label} çalışıyor...
            </span>
            {jobData && <Badge value={jobData.status} />}
          </div>
          <Progress value={jobData?.progress_pct ?? 0} />
          {jobData?.progress_message && (
            <p className="font-mono text-[12px] text-muted">{jobData.progress_message}</p>
          )}
        </div>
      )}

      {error && (
        <div className="border border-hot/40 bg-hot/5 p-3 font-mono text-[12px] text-hot">
          {error}
        </div>
      )}
    </div>
  );
}
