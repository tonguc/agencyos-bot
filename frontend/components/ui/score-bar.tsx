import { cn } from "@/lib/utils";

interface ScoreBarProps {
  label: string;
  value: number | null;
}

function getColor(v: number): { fill: string; text: string } {
  if (v >= 65) return { fill: "from-ok to-teal-400", text: "text-ok" };
  if (v >= 35) return { fill: "from-warm to-orange-400", text: "text-warm" };
  return { fill: "from-hot to-red-600", text: "text-hot" };
}

export function ScoreBar({ label, value }: ScoreBarProps) {
  const v = value ?? 0;
  const c = getColor(v);
  return (
    <div>
      <div className="flex justify-between text-[10px] font-mono mb-1.5 tracking-wider">
        <span className="text-muted uppercase">{label}</span>
        <span className={cn("font-bold", c.text)}>{v}</span>
      </div>
      <div className="h-1 w-full bg-stroke overflow-hidden">
        <div
          className={cn("h-full bg-gradient-to-r transition-all", c.fill)}
          style={{ width: `${Math.max(v, 3)}%` }}
        />
      </div>
    </div>
  );
}
