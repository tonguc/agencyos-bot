import { cn } from "@/lib/utils";

const variants: Record<string, string> = {
  default:   "text-muted border-stroke",
  yeni:      "text-accent border-accent/50 bg-accent/5",
  audit:     "text-review border-review/50 bg-review/5",
  mesaj:     "text-warm border-warm/50 bg-warm/5",
  cevap:     "text-orange-400 border-orange-400/40 bg-orange-400/5",
  demo:      "text-pink-400 border-pink-400/40 bg-pink-400/5",
  teklif:    "text-ok border-ok/50 bg-ok/5",
  kapandi:   "text-ok border-ok/30 bg-ok/5",
  soguk:     "text-dim border-dim/50",
  pending:   "text-warm border-warm/50 bg-warm/5",
  running:   "text-accent border-accent/50 bg-accent/5",
  completed: "text-ok border-ok/50 bg-ok/5",
  failed:    "text-hot border-hot/50 bg-hot/5",
  yuksek:    "text-hot border-hot/50 bg-hot/5",
  orta:      "text-warm border-warm/50 bg-warm/5",
  dusuk:     "text-dim border-dim/50",
  sicak:     "text-hot border-hot/50 bg-hot/5",
  ilik:      "text-warm border-warm/50 bg-warm/5",
  önerilen:  "text-ok border-ok/50 bg-ok/5",
  gönderildi:"text-accent border-accent/50 bg-accent/5",
};

const DISPLAY: Record<string, string> = {
  kapandi:   "Kapandı",
  soguk:     "Soğuk",
};

interface BadgeProps {
  value: string;
  className?: string;
}

export function Badge({ value, className }: BadgeProps) {
  const key = value.toLowerCase();
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-2 py-0.5 text-[9px] font-mono font-medium tracking-[0.2em] uppercase",
        variants[key] ?? variants.default,
        className
      )}
    >
      {DISPLAY[key] ?? value}
    </span>
  );
}
