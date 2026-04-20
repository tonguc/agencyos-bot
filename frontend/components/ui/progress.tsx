import { cn } from "@/lib/utils";

interface ProgressProps {
  value: number;
  className?: string;
  color?: "accent" | "ok" | "hot";
}

export function Progress({ value, className, color = "accent" }: ProgressProps) {
  const fills = {
    accent: "from-accent to-blue-400",
    ok:     "from-ok to-teal-400",
    hot:    "from-hot to-red-600",
  };
  return (
    <div className={cn("h-1 w-full bg-stroke overflow-hidden", className)}>
      <div
        className={cn("h-full bg-gradient-to-r transition-all duration-300", fills[color])}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}
