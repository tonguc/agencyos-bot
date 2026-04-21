import type { SearchSegment } from "@/types";

export const SEGMENT_LABELS: Record<SearchSegment, string> = {
  hot:    "Fırsat",
  warm:   "Aday",
  ok:     "Orta",
  low:    "Elendi",
  review: "İncele",
};

export const SEGMENT_COLORS: Record<
  SearchSegment,
  { color: string; dot: string; text: string; border: string }
> = {
  hot:    { color: "#e53935", dot: "bg-hot",    text: "text-hot",    border: "border-hot" },
  warm:   { color: "#fb8c00", dot: "bg-warm",   text: "text-warm",   border: "border-warm" },
  ok:     { color: "#6b8db5", dot: "bg-ok",     text: "text-ok",     border: "border-ok" },
  low:    { color: "#9e9e9e", dot: "bg-low",    text: "text-low",    border: "border-low" },
  review: { color: "#d4a017", dot: "bg-review", text: "text-review", border: "border-review" },
};
