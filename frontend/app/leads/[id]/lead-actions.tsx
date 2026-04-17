"use client";

import { useState, useEffect, useRef } from "react";
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
}

interface RunningJob {
  id: string;
  label: string;
}

export function LeadActions({ leadId, hasAudit, hasOutreach, hasProposal, proposalId }: Props) {
  const router = useRouter();
  const [runningJob, setRunningJob] = useState<RunningJob | null>(null);
  const [jobData, setJobData] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  function startPolling(jobId: string) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const job = await jobsApi.get(jobId);
        setJobData(job);
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
        // transient fetch error, keep polling
      }
    }, 1500);
  }

  async function trigger(
    label: string,
    fn: () => Promise<{ job_id: string; status: string }>
  ) {
    setError(null);
    setJobData(null);
    try {
      const res = await fn();
      setRunningJob({ id: res.job_id, label });
      startPolling(res.job_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Hata oluştu");
    }
  }

  const busy = runningJob !== null;

  return (
    <div className="space-y-3">
      {/* Action buttons */}
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
          <a
            href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/proposals/${proposalId}/pdf`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button size="sm" variant="outline">PDF İndir ↓</Button>
          </a>
        )}
      </div>

      {/* Job progress */}
      {runningJob && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-blue-700">{runningJob.label} çalışıyor...</span>
            {jobData && <Badge value={jobData.status} />}
          </div>
          <Progress value={jobData?.progress_pct ?? 0} />
          {jobData?.progress_message && (
            <p className="text-xs text-blue-600">{jobData.progress_message}</p>
          )}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}
    </div>
  );
}
