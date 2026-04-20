import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Score thresholds — scorer'in route_decision'i ile hizali.
// Tek kaynak; tum UI buradan tuketir. Backend: backend/core/lead_scorer.py.
export const SCORE_HOT  = 80;
export const SCORE_WARM = 60;

export function scoreColorClass(v: number | null | undefined): string {
  const n = v ?? -1;
  if (n >= SCORE_HOT)  return "text-hot";
  if (n >= SCORE_WARM) return "text-warm";
  return "text-dim";
}

export function scoreHex(v: number | null | undefined): string {
  const n = v ?? -1;
  if (n >= SCORE_HOT)  return "#ff3b4a";
  if (n >= SCORE_WARM) return "#ffb648";
  return "#7a8aa8";
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("tr-TR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("tr-TR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
