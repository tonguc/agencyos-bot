import { cn } from "@/lib/utils";

const variants: Record<string, string> = {
  default: "bg-slate-100 text-slate-700",
  yeni: "bg-blue-100 text-blue-700",
  audit: "bg-violet-100 text-violet-700",
  mesaj: "bg-yellow-100 text-yellow-700",
  cevap: "bg-orange-100 text-orange-700",
  demo: "bg-pink-100 text-pink-700",
  teklif: "bg-emerald-100 text-emerald-700",
  kapandi: "bg-green-100 text-green-700",
  soguk: "bg-slate-100 text-slate-500",
  // job statuses
  pending: "bg-yellow-100 text-yellow-700",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  // urgency / lead quality
  yuksek: "bg-red-100 text-red-700",
  orta: "bg-orange-100 text-orange-700",
  dusuk: "bg-slate-100 text-slate-600",
  sicak: "bg-red-100 text-red-700",
  ilik: "bg-orange-100 text-orange-700",
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
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        variants[key] ?? variants.default,
        className
      )}
    >
      {value}
    </span>
  );
}
