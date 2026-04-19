import type { SearchSegment } from "@/types";

export const SEGMENT_LABELS: Record<SearchSegment, string> = {
  hot:    "Fırsat",
  warm:   "Aday",
  ok:     "Orta",
  low:    "Elendi",
  review: "Kontrol",
};

export const SEGMENT_COLORS: Record<
  SearchSegment,
  { color: string; dot: string; text: string; border: string }
> = {
  hot:    { color: "#ff3b4a", dot: "bg-hot",    text: "text-hot",    border: "border-hot" },
  warm:   { color: "#ffb648", dot: "bg-warm",   text: "text-warm",   border: "border-warm" },
  ok:     { color: "#34d399", dot: "bg-ok",     text: "text-ok",     border: "border-ok" },
  low:    { color: "#64748b", dot: "bg-low",    text: "text-low",    border: "border-low" },
  review: { color: "#a774ff", dot: "bg-review", text: "text-review", border: "border-review" },
};
