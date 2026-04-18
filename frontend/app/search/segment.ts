import type { SearchSegment } from "@/types";

export const SEGMENT_LABELS: Record<SearchSegment, string> = {
  hot:    "Sıcak",
  warm:   "Ilık",
  ok:     "Uygun",
  low:    "Zayıf",
  review: "Gözden Geçir",
};

export const SEGMENT_COLORS: Record<SearchSegment, { dot: string; bg: string; text: string; border: string; ring: string }> = {
  hot:    { dot: "bg-red-500",    bg: "bg-red-50",    text: "text-red-700",    border: "border-red-200",    ring: "ring-red-400" },
  warm:   { dot: "bg-amber-500",  bg: "bg-amber-50",  text: "text-amber-700",  border: "border-amber-200",  ring: "ring-amber-400" },
  ok:     { dot: "bg-blue-500",   bg: "bg-blue-50",   text: "text-blue-700",   border: "border-blue-200",   ring: "ring-blue-400" },
  low:    { dot: "bg-slate-400",  bg: "bg-slate-50",  text: "text-slate-600",  border: "border-slate-200",  ring: "ring-slate-400" },
  review: { dot: "bg-purple-500", bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200", ring: "ring-purple-400" },
};
