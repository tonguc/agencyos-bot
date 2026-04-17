import { cn } from "@/lib/utils";

interface ScoreBarProps {
  label: string;
  value: number | null;
}

function color(v: number) {
  if (v >= 70) return "bg-green-500";
  if (v >= 40) return "bg-orange-400";
  return "bg-red-500";
}

export function ScoreBar({ label, value }: ScoreBarProps) {
  const v = value ?? 0;
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-500">{label}</span>
        <span className="font-medium text-slate-700">{v}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", color(v))} style={{ width: `${v}%` }} />
      </div>
    </div>
  );
}
